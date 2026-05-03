import asyncio
import json
from celery import Task
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.workers.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()


def _make_session() -> async_sessionmaker:
    """Create a fresh engine + session factory with NullPool for each Celery task run.
    NullPool avoids event-loop mismatch errors when asyncio.run() is called repeatedly."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class DatabaseTask(Task):
    """Base task that provides an async DB session."""
    abstract = True

    def _get_session(self):
        from app.core.database import AsyncSessionLocal
        return AsyncSessionLocal()


@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.generate_plan_task",
                 max_retries=2, default_retry_delay=5)
def generate_plan_task(self, plan_id: int):
    """
    Async plan generation task.
    Runs the coroutine in a fresh event loop inside the Celery worker.
    """
    asyncio.run(_generate_plan(self, plan_id))


async def _generate_plan(task: Task, plan_id: int):
    from sqlalchemy import select
    from app.models.pitch_plan import PitchPlan, PlanPage
    from app.models.pitch_task import PitchTask
    from app.services.ppt_parser import parse_pptx
    from app.services.llm_adapter import generate_pitch_plan
    from app.core.storage import download_bytes, upload_bytes
    from app.core.ws_manager import publish_progress

    async with _make_session()() as db:
        result = await db.execute(select(PitchPlan).where(PitchPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            return

        task_result = await db.execute(select(PitchTask).where(PitchTask.id == plan.pitch_task_id))
        pitch_task = task_result.scalar_one_or_none()

        async def progress(pct: int, stage: str):
            await publish_progress(
                redis_url=settings.redis_url,
                tenant_id=plan.tenant_id,
                entity_type="plan",
                entity_id=plan_id,
                progress=pct,
                stage=stage,
            )

        try:
            await progress(5, "downloading_ppt")
            ppt_bytes = download_bytes(plan.ppt_file_id)

            await progress(15, "parsing_ppt")
            parsed = parse_pptx(ppt_bytes)

            # Upload thumbnails
            thumbnail_urls: dict[int, str] = {}
            for page in parsed.pages:
                if page.thumbnail_bytes:
                    key = f"{plan.tenant_id}/pitch-coach/plans/{plan_id}/thumb_{page.page_number}.png"
                    upload_bytes(key, page.thumbnail_bytes, "image/png")
                    from app.core.storage import get_presigned_download_url
                    thumbnail_urls[page.page_number] = key

            await progress(30, "generating_plan")

            raw_pages = [
                {
                    "page_number": p.page_number,
                    "title": p.title,
                    "content": p.content,
                    "speaker_notes": p.speaker_notes,
                }
                for p in parsed.pages
            ]

            # Search knowledge base for relevant context (best-effort; skip on failure)
            knowledge_context: list[dict] | None = None
            try:
                from app.services.knowledge_service import hybrid_search
                query_terms = " ".join(filter(None, [
                    plan.customer_industry,
                    pitch_task.name if pitch_task else plan.ppt_file_name,
                    plan.bid_requirements[:100] if plan.bid_requirements else None,
                ]))
                if query_terms.strip():
                    hits = await hybrid_search(
                        query=query_terms,
                        tenant_id=plan.tenant_id,
                        db=db,
                        top_n=5,
                    )
                    if hits:
                        knowledge_context = hits
            except Exception as kb_err:
                import logging
                logging.getLogger(__name__).warning(f"Knowledge search skipped: {kb_err}")

            # Choose model based on subscription tier (free → lite model to reduce cost)
            from app.models.subscription import Subscription
            sub_res = await db.execute(
                select(Subscription).where(
                    Subscription.tenant_id == plan.tenant_id,
                    Subscription.status.in_(["trial", "active"]),
                )
            )
            is_paid = sub_res.scalar_one_or_none() is not None
            llm_model_to_use = settings.llm_model if is_paid else settings.llm_model_lite

            llm_result = await generate_pitch_plan(
                project_name=pitch_task.name if pitch_task else plan.ppt_file_name,
                customer_name=plan.customer_name or "",
                customer_industry=plan.customer_industry or "",
                project_budget=str(plan.project_budget or ""),
                bid_time_limit=plan.bid_time_limit or 30,
                bid_requirements=plan.bid_requirements or "",
                competitor_info=plan.competitor_info or [],
                pages=raw_pages,
                knowledge_context=knowledge_context,
                progress_callback=progress,
                model=llm_model_to_use,
            )

            await progress(90, "saving_results")

            # Remove any previously saved pages (handles retries)
            from sqlalchemy import delete as sa_delete
            await db.execute(sa_delete(PlanPage).where(PlanPage.plan_id == plan_id))
            await db.flush()

            gs = llm_result.get("global_strategy", {})
            plan.global_strategy = json.dumps(gs, ensure_ascii=False)
            plan.total_duration_sec = gs.get("total_duration_sec")
            plan.predicted_questions = llm_result.get("predicted_questions", [])
            plan.competitive_differentiation = llm_result.get("competitive_differentiation", [])
            plan.opening_templates = llm_result.get("opening_templates", [])
            plan.closing_templates = llm_result.get("closing_templates", [])
            plan.ppt_page_count = parsed.page_count
            plan.status = 1  # completed

            # Save plan pages
            for p_data in llm_result.get("pages", []):
                pnum = p_data.get("page_number")
                parsed_page = next((p for p in parsed.pages if p.page_number == pnum), None)

                page = PlanPage(
                    plan_id=plan_id,
                    page_number=pnum,
                    page_title=parsed_page.title if parsed_page else "",
                    page_content_summary=parsed_page.content[:500] if parsed_page else "",
                    page_thumbnail_url=thumbnail_urls.get(pnum),
                    importance_level=p_data.get("importance_level", 2),
                    talking_points=p_data.get("talking_points", []),
                    suggested_duration=p_data.get("suggested_duration_sec", 60),
                    emphasis_marks=p_data.get("emphasis_marks"),
                    bid_req_mapping=p_data.get("bid_req_mapping"),
                    transition_hint=p_data.get("transition_hint"),
                )
                db.add(page)

            await db.commit()
            await progress(100, "done")

        except Exception as exc:
            plan.status = 4  # error (we add this status)
            await db.commit()
            await progress(0, f"error: {str(exc)[:100]}")
            raise task.retry(exc=exc)


# ---------------------------------------------------------------------------
# Rehearsal scoring task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.score_rehearsal_task",
                 max_retries=1, default_retry_delay=5)
def score_rehearsal_task(self, rehearsal_id: int):
    asyncio.run(_score_rehearsal(self, rehearsal_id))


async def _score_rehearsal(task: Task, rehearsal_id: int):
    from sqlalchemy import select
    from app.models.rehearsal import Rehearsal
    from app.models.pitch_plan import PitchPlan, PlanPage
    from app.services.asr_adapter import transcribe
    from app.services.scoring_engine import score_rehearsal
    from app.core.storage import download_bytes
    from app.core.ws_manager import publish_progress

    async with _make_session()() as db:
        rehearsal = await db.get(Rehearsal, rehearsal_id)
        if not rehearsal:
            return

        async def progress(pct: int, stage: str):
            await publish_progress(
                redis_url=settings.redis_url,
                tenant_id=rehearsal.tenant_id,
                entity_type="rehearsal",
                entity_id=rehearsal_id,
                progress=pct,
                stage=stage,
            )

        try:
            await progress(10, "downloading_audio")
            audio_bytes = download_bytes(rehearsal.audio_url)

            await progress(20, "transcribing")
            rehearsal.status = 1  # transcribing
            await db.commit()

            segments = await transcribe(audio_bytes)
            rehearsal.transcript_json = segments

            await progress(60, "scoring")
            rehearsal.status = 2  # scoring
            await db.commit()

            # Load plan pages for timing reference
            plan_pages_data: list[dict] = []
            if rehearsal.plan_id:
                result = await db.execute(
                    select(PlanPage).where(PlanPage.plan_id == rehearsal.plan_id)
                )
                plan_pages = result.scalars().all()
                plan_pages_data = [
                    {
                        "page_number": p.page_number,
                        "importance_level": p.importance_level,
                        "suggested_duration_sec": p.suggested_duration or 60,
                    }
                    for p in plan_pages
                ]

            # Load target duration from plan
            target_sec = 1200
            if rehearsal.plan_id:
                plan = await db.get(PitchPlan, rehearsal.plan_id)
                if plan and plan.total_duration_sec:
                    target_sec = int(plan.total_duration_sec)

            result = score_rehearsal(
                transcript_segments=segments,
                page_timings=rehearsal.page_timings or [],
                plan_pages=plan_pages_data,
                target_duration_sec=target_sec,
            )

            rehearsal.total_score = result.total_score
            rehearsal.dimension_scores = {
                "fluency": result.fluency_score,
                "rate": result.rate_score,
                "timing": result.timing_score,
                "chars_per_min": result.chars_per_min,
                "total_duration_sec": result.total_duration_sec,
            }
            rehearsal.filler_word_count = result.filler_count
            rehearsal.filler_word_detail = result.filler_detail
            rehearsal.improvement_tips = result.improvement_tips
            rehearsal.page_scores = result.page_scores
            rehearsal.status = 3  # scored

            await db.commit()
            await progress(100, "done")

        except Exception as exc:
            rehearsal.status = 6  # error / needs improvement
            await db.commit()
            await progress(0, f"error: {str(exc)[:100]}")
            raise task.retry(exc=exc)


# ---------------------------------------------------------------------------
# Narration generation task (F2 AI 示范讲解)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.generate_narration_task",
                 max_retries=1, default_retry_delay=10)
def generate_narration_task(self, narration_id: int):
    asyncio.run(_generate_narration(self, narration_id))


async def _generate_narration(task: Task, narration_id: int):
    from sqlalchemy import select
    from app.models.narration import DemoNarration
    from app.models.pitch_plan import PitchPlan, PlanPage
    from app.services.llm_adapter import generate_page_scripts
    from app.services.tts_adapter import text_to_speech
    from app.core.storage import upload_bytes, download_bytes
    from app.core.ws_manager import publish_progress
    import asyncio
    import tempfile
    import os
    import subprocess

    async with _make_session()() as db:
        narration = await db.get(DemoNarration, narration_id)
        if not narration:
            return

        async def progress(pct: int, stage: str):
            await publish_progress(
                redis_url=settings.redis_url,
                tenant_id=narration.tenant_id,
                entity_type="narration",
                entity_id=narration_id,
                progress=pct,
                stage=stage,
            )

        try:
            await progress(5, "loading_plan")

            plan = await db.get(PitchPlan, narration.plan_id)
            if not plan:
                raise ValueError(f"Plan {narration.plan_id} not found")

            result = await db.execute(
                select(PlanPage)
                .where(PlanPage.plan_id == narration.plan_id)
                .order_by(PlanPage.page_number)
            )
            plan_pages = result.scalars().all()
            if not plan_pages:
                raise ValueError("Plan has no pages")

            # Step 1: Generate scripts via LLM
            await progress(10, "generating_scripts")
            narration.status = 1
            await db.commit()

            pages_for_llm = [
                {
                    "page_number": p.page_number,
                    "page_title": p.page_title or "",
                    "talking_points": p.talking_points or [],
                    "importance_level": p.importance_level,
                    "suggested_duration": p.suggested_duration or 60,
                }
                for p in plan_pages
            ]

            import asyncio as _asyncio
            pitch_task_name = plan.ppt_file_name
            if plan.pitch_task_id:
                from app.models.pitch_task import PitchTask
                pt = await db.get(PitchTask, plan.pitch_task_id)
                if pt:
                    pitch_task_name = pt.name

            scripts = await generate_page_scripts(
                pages=pages_for_llm,
                project_name=pitch_task_name,
                bid_time_limit=plan.bid_time_limit or 30,
            )
            # Build a lookup {page_number: script_data}
            script_map = {s["page_number"]: s for s in scripts}

            # Step 2: Synthesize each page
            await progress(20, "synthesizing")
            narration.status = 2
            await db.commit()

            page_audios: list[dict] = []
            n_pages = len(plan_pages)

            # Synthesize up to 5 pages concurrently
            CONCURRENCY = 5

            async def _synth_page(p: PlanPage) -> dict:
                script_data = script_map.get(p.page_number, {})
                script_text = script_data.get("script", f"第{p.page_number}页讲解内容")
                duration_est = script_data.get("duration_estimate_sec", p.suggested_duration or 60)

                audio_bytes = await text_to_speech(
                    text=script_text,
                    voice_id=narration.voice_id,
                    speed=narration.speed,
                    fmt="mp3",
                )
                key = (
                    f"{narration.tenant_id}/pitch-coach/narrations/"
                    f"{narration_id}/page_{p.page_number}.mp3"
                )
                upload_bytes(key, audio_bytes, "audio/mpeg")
                return {
                    "page_number": p.page_number,
                    "script": script_text,
                    "tone": script_data.get("tone", "稳健型"),
                    "audio_url": key,
                    "duration_sec": duration_est,
                }

            sem = _asyncio.Semaphore(CONCURRENCY)

            async def _synth_with_sem(p):
                async with sem:
                    return await _synth_page(p)

            page_audios = list(await _asyncio.gather(*[_synth_with_sem(p) for p in plan_pages]))
            page_audios.sort(key=lambda x: x["page_number"])

            # Step 3: Merge all page MP3s with FFmpeg
            await progress(80, "merging")
            narration.status = 3
            await db.commit()

            total_audio_key = (
                f"{narration.tenant_id}/pitch-coach/narrations/{narration_id}/full.mp3"
            )
            total_dur = await _merge_audio(
                narration_id=narration_id,
                page_audios=page_audios,
                output_key=total_audio_key,
                download_fn=download_bytes,
                upload_fn=upload_bytes,
            )

            narration.page_audios = page_audios
            narration.total_audio_url = total_audio_key
            narration.total_duration_sec = total_dur
            narration.status = 4  # ready
            await db.commit()
            await progress(100, "done")

        except Exception as exc:
            narration.status = 5  # error
            narration.error_msg = str(exc)[:500]
            await db.commit()
            await progress(0, f"error: {str(exc)[:100]}")
            raise task.retry(exc=exc)


async def _merge_audio(
    narration_id: int,
    page_audios: list[dict],
    output_key: str,
    download_fn,
    upload_fn,
) -> int:
    """Merge page MP3 files with 0.8s silence between pages using FFmpeg."""
    import subprocess
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmp:
        input_files: list[str] = []

        # Write a 0.8s silent WAV for padding
        from app.services.tts_adapter import _stub_wav, PAGE_PAUSE_MS
        silence_bytes = _stub_wav(PAGE_PAUSE_MS / 1000)
        silence_path = os.path.join(tmp, "silence.wav")
        with open(silence_path, "wb") as f:
            f.write(silence_bytes)

        for i, pa in enumerate(page_audios):
            page_bytes = download_fn(pa["audio_url"])
            page_path = os.path.join(tmp, f"page_{i:03d}.mp3")
            with open(page_path, "wb") as f:
                f.write(page_bytes)
            input_files.append(page_path)
            if i < len(page_audios) - 1:
                input_files.append(silence_path)

        # Build FFmpeg concat filter list
        concat_list_path = os.path.join(tmp, "concat.txt")
        with open(concat_list_path, "w") as f:
            for path in input_files:
                f.write(f"file '{path}'\n")

        output_path = os.path.join(tmp, "full.mp3")
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list_path,
                    "-acodec", "libmp3lame", "-q:a", "4",
                    output_path,
                ],
                capture_output=True,
                timeout=120,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # FFmpeg not available or error — concatenate raw bytes as fallback
            all_bytes = b""
            for path in input_files:
                with open(path, "rb") as f:
                    all_bytes += f.read()
            with open(output_path, "wb") as f:
                f.write(all_bytes)

        with open(output_path, "rb") as f:
            merged_bytes = f.read()

        upload_fn(output_key, merged_bytes, "audio/mpeg")

        # Estimate total duration from page durations + pauses
        total_dur = sum(pa.get("duration_sec", 60) for pa in page_audios)
        total_dur += int(PAGE_PAUSE_MS / 1000) * (len(page_audios) - 1)
        return total_dur


# ---------------------------------------------------------------------------
# Knowledge base ingestion task (P1 知识库)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.ingest_document_task",
                 max_retries=1, default_retry_delay=30)
def ingest_document_task(self, doc_id: int):
    asyncio.run(_ingest_document(self, doc_id))


async def _ingest_document(task: Task, doc_id: int):
    from app.services.knowledge_service import ingest_document

    async with _make_session()() as db:
        try:
            await ingest_document(doc_id, db)
        except Exception as exc:
            raise task.retry(exc=exc)


# ---------------------------------------------------------------------------
# Monthly usage reset (Celery Beat — 1st of every month at 00:00 CST)
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.tasks.reset_monthly_usage_task")
def reset_monthly_usage_task():
    asyncio.run(_reset_monthly_usage())


async def _reset_monthly_usage():
    """
    Reset usage_meter counters for the PREVIOUS month.
    The upsert-based quota_service accumulates counts in the current month row.
    We don't delete old rows (they serve as audit history); we just log the reset.
    No DB writes needed: quota_service uses (user_id, feature, year_month) as the PK
    so the new month automatically starts at 0 when the first event is recorded.
    This task simply logs the rollover and can be extended with notification logic.
    """
    import logging
    from datetime import date

    logger = logging.getLogger(__name__)
    today = date.today()
    logger.info(
        "Monthly usage rollover: %s-%02d → %s-%02d",
        today.year if today.month > 1 else today.year - 1,
        today.month - 1 if today.month > 1 else 12,
        today.year,
        today.month,
    )
    # Optional: send summary email / Slack notification (P2)


# ---------------------------------------------------------------------------
# Bid deadline 48h warning (Celery Beat — every hour)
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.tasks.bid_deadline_warning_task")
def bid_deadline_warning_task():
    asyncio.run(_bid_deadline_warning())


async def _bid_deadline_warning():
    """
    Scan pitch_task rows where bid_date is between 24h and 48h from now.
    Log the upcoming deadlines (webhook / notification in P2).
    """
    import logging
    from datetime import datetime, timedelta

    logger = logging.getLogger(__name__)

    async with _make_session()() as db:
        from sqlalchemy import select, text
        now = datetime.utcnow()
        window_start = now + timedelta(hours=24)
        window_end = now + timedelta(hours=48)

        result = await db.execute(
            text(
                """
                SELECT id, name, tenant_id, bid_date
                FROM pitch_task
                WHERE bid_date BETWEEN :start AND :end
                  AND status != 3
                """
            ),
            {"start": window_start, "end": window_end},
        )
        rows = result.fetchall()
        for row in rows:
            logger.info(
                "48h bid warning — task_id=%s name=%s bid_date=%s tenant_id=%s",
                row.id, row.name, row.bid_date, row.tenant_id,
            )

            # Push to enterprise IM (企微/飞书/钉钉)
            try:
                from app.services.notification_webhook import notify_bid_deadline
                from datetime import timezone
                bid_dt = row.bid_date
                if hasattr(bid_dt, 'tzinfo') and bid_dt.tzinfo is None:
                    bid_dt = bid_dt.replace(tzinfo=timezone.utc)
                hours_left = max(0, int((bid_dt - now.replace(tzinfo=timezone.utc)).total_seconds() / 3600))

                # Compute readiness score (count completed SOP steps)
                from app.models.pitch_task import PitchTask
                from app.models.user import PcUser
                task_obj = await db.get(PitchTask, row.id)
                readiness_pct = getattr(task_obj, 'readiness_score', 0) or 0

                # Get responsible user name
                responsible_name = "团队成员"
                if task_obj and task_obj.created_by:
                    user_obj = await db.get(PcUser, task_obj.created_by)
                    if user_obj:
                        responsible_name = user_obj.name or user_obj.email or responsible_name

                results = notify_bid_deadline(
                    task_name=row.name,
                    hours_left=hours_left,
                    responsible_name=responsible_name,
                    readiness_pct=readiness_pct,
                )
                if results:
                    logger.info("Bid deadline notification sent: %s", results)
            except Exception as notify_err:
                logger.warning("Bid deadline notification failed: %s", notify_err)


# ---------------------------------------------------------------------------
# Trial expiry (Celery Beat — every hour)
# ---------------------------------------------------------------------------

@celery_app.task(name="app.workers.tasks.expire_trials_task")
def expire_trials_task():
    asyncio.run(_expire_trials())


async def _expire_trials():
    """
    Find subscription rows in 'trial' status whose trial_ends_at has passed,
    and downgrade them back to 'free'.
    """
    import logging
    from datetime import datetime

    logger = logging.getLogger(__name__)

    async with _make_session()() as db:
        from sqlalchemy import select, text
        from app.models.subscription import Subscription

        now = datetime.utcnow()
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == "trial",
                Subscription.trial_ends_at <= now,
            )
        )
        expired = result.scalars().all()
        for sub in expired:
            sub.status = "expired"
            sub.plan_type = "free"
            sub.updated_at = now
            logger.info("Trial expired — tenant_id=%s", sub.tenant_id)
        if expired:
            await db.commit()
            logger.info("Expired %d trials", len(expired))


# ---------------------------------------------------------------------------
# Post-Mortem analysis task (F7 AI 复盘助手)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, base=DatabaseTask, name="app.workers.tasks.run_post_mortem_task",
                 max_retries=1, default_retry_delay=10)
def run_post_mortem_task(self, post_mortem_id: int):
    asyncio.run(_run_post_mortem(self, post_mortem_id))


async def _run_post_mortem(task: Task, post_mortem_id: int):
    """
    AI 复盘分析完整流程：
    1. ASR 转录录音
    2. 说话人分离（LLM 推断）
    3. 评委问题提取 + 分类
    4. 与排练预测对比（命中率）
    5. 回答质量评估
    6. 答疑函草拟
    7. 关键时刻提取
    8. 综合洞察生成
    """
    import logging
    from app.core.storage import download_bytes
    from app.core.ws_manager import publish_progress

    logger = logging.getLogger(__name__)

    async with _make_session()() as db:
        from app.models.post_mortem import PostMortem
        from app.models.pitch_task import PitchTask
        from app.models.pitch_plan import PitchPlan
        from app.services.asr_adapter import transcribe
        from app.services.post_mortem_service import run_full_post_mortem

        pm = await db.get(PostMortem, post_mortem_id)
        if not pm:
            return

        async def progress(pct: int, stage: str):
            await publish_progress(
                redis_url=settings.redis_url,
                tenant_id=pm.tenant_id,
                entity_type="post_mortem",
                entity_id=post_mortem_id,
                progress=pct,
                stage=stage,
            )

        try:
            pm.status = "processing"
            await db.commit()

            await progress(5, "downloading_recording")

            # 1. Download and transcribe
            audio_bytes = download_bytes(pm.recording_url)
            await progress(15, "transcribing")
            segments = await transcribe(audio_bytes)
            # Build full transcript text for LLM
            transcript_text = " ".join(
                seg.get("text", "") for seg in (segments or [])
            ).strip()
            if not transcript_text:
                raise ValueError("Transcript is empty — ASR returned no text")

            # 2. Get task info for context
            pitch_task = await db.get(PitchTask, pm.pitch_task_id)
            task_name = pitch_task.name if pitch_task else "述标项目"
            customer_name = (pitch_task.customer_name or "") if pitch_task else ""

            # 3. Get predicted questions from latest plan
            predicted_questions: list[str] = []
            try:
                from sqlalchemy import select
                from app.models.pitch_plan import PitchPlan
                plan_result = await db.execute(
                    select(PitchPlan)
                    .where(
                        PitchPlan.pitch_task_id == pm.pitch_task_id,
                        PitchPlan.status == 1,
                    )
                    .order_by(PitchPlan.id.desc())
                    .limit(1)
                )
                latest_plan = plan_result.scalar_one_or_none()
                if latest_plan and latest_plan.predicted_questions:
                    predicted_questions = latest_plan.predicted_questions or []
            except Exception:
                pass

            # 4. Get knowledge base context (best-effort)
            kb_context = ""
            try:
                from app.services.knowledge_service import hybrid_search
                hits = await hybrid_search(
                    query=task_name,
                    tenant_id=pm.tenant_id,
                    db=db,
                    top_n=3,
                )
                if hits:
                    kb_context = "\n".join(h.get("content", "") for h in hits[:3])
            except Exception as kb_err:
                logger.warning("KB search skipped: %s", kb_err)

            await progress(30, "analyzing")

            # 5. Run full analysis
            result = await run_full_post_mortem(
                transcript_text=transcript_text,
                task_name=task_name,
                customer_name=customer_name,
                predicted_questions=predicted_questions,
                kb_context=kb_context,
            )

            await progress(90, "saving")

            # 6. Persist results
            pm.diarization = result["diarization"]
            pm.evaluator_questions = result["evaluator_questions"]
            pm.our_talk_ratio = result["our_talk_ratio"]
            pm.evaluator_count = result["evaluator_count"]
            pm.question_count = result["question_count"]
            pm.question_categories = result["question_categories"]
            pm.prediction_hit_rate = result["prediction_hit_rate"]
            pm.answer_assessments = result["answer_assessments"]
            pm.followup_draft = result["followup_draft"]
            pm.key_moments = result["key_moments"]
            pm.insights = result["insights"]
            pm.status = "completed"

            await db.commit()
            await progress(100, "done")

        except Exception as exc:
            pm.status = "failed"
            pm.error_msg = str(exc)[:512]
            await db.commit()
            await progress(0, f"error: {str(exc)[:100]}")
            logger.exception("Post-mortem task failed for id=%s", post_mortem_id)
            raise task.retry(exc=exc)
