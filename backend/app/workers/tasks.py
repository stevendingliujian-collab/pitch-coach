import asyncio
import json
from celery import Task
from app.workers.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()


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
    from app.core.database import AsyncSessionLocal
    from app.models.pitch_plan import PitchPlan, PlanPage
    from app.models.pitch_task import PitchTask
    from app.services.ppt_parser import parse_pptx
    from app.services.llm_adapter import generate_pitch_plan
    from app.core.storage import download_bytes, upload_bytes
    from app.core.ws_manager import ws_manager

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PitchPlan).where(PitchPlan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            return

        task_result = await db.execute(select(PitchTask).where(PitchTask.id == plan.pitch_task_id))
        pitch_task = task_result.scalar_one_or_none()

        async def progress(pct: int, stage: str):
            await ws_manager.send_progress(
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

            llm_result = await generate_pitch_plan(
                project_name=pitch_task.name if pitch_task else plan.ppt_file_name,
                customer_name=plan.customer_name or "",
                customer_industry=plan.customer_industry or "",
                project_budget=str(plan.project_budget or ""),
                bid_time_limit=plan.bid_time_limit or 30,
                bid_requirements=plan.bid_requirements or "",
                competitor_info=plan.competitor_info or [],
                pages=raw_pages,
                progress_callback=progress,
            )

            await progress(90, "saving_results")

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
    from app.core.database import AsyncSessionLocal
    from app.models.rehearsal import Rehearsal
    from app.models.pitch_plan import PitchPlan, PlanPage
    from app.services.asr_adapter import transcribe
    from app.services.scoring_engine import score_rehearsal
    from app.core.storage import download_bytes
    from app.core.ws_manager import ws_manager

    async with AsyncSessionLocal() as db:
        rehearsal = await db.get(Rehearsal, rehearsal_id)
        if not rehearsal:
            return

        async def progress(pct: int, stage: str):
            await ws_manager.send_progress(
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
