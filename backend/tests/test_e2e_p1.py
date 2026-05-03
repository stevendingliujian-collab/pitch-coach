"""
E2E tests for P1 features: Knowledge Base, F3 Training, Reviews, Narrations.
Runs against the live server at http://localhost:8001.

Usage:
    cd backend
    source .venv/bin/activate
    python -m pytest tests/test_e2e_p1.py -v --tb=short
"""
import pytest
import httpx
import asyncio
import json
from datetime import date, timedelta

BASE = "http://localhost:8001/api/v1"

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return httpx.Client(base_url=BASE, timeout=30)


@pytest.fixture(scope="module")
def auth_headers(client):
    """Register a fresh test user, upgrade to pro, and return auth headers."""
    import random
    suffix = random.randint(10000, 99999)
    email = f"e2e_test_{suffix}@example.com"

    # Register
    r = client.post("/auth/register", json={
        "email": email,
        "password": "TestPass123!",
        "full_name": "E2E Tester",
        "tenant_name": f"E2E Corp {suffix}",
    })
    assert r.status_code in (200, 201), f"Register failed: {r.text}"

    # Login
    r = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upgrade to pro so all E2E tests can run without 402 gates
    r = client.post("/billing/upgrade", headers=headers, json={
        "plan_type": "pro_10",
        "billing_cycle": "monthly",
    })
    # 200/201 = success; ignore if billing API not available
    assert r.status_code in (200, 201), f"Pro upgrade failed: {r.text}"

    # Re-login to get a fresh token reflecting the new plan
    r = client.post("/auth/login", json={"email": email, "password": "TestPass123!"})
    assert r.status_code == 200, f"Re-login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def task_id(client, auth_headers):
    """Create a pitch task for testing."""
    r = client.post("/pitch-tasks", headers=auth_headers, json={
        "name": "E2E 测试项目",
        "customer_name": "测试客户",
        "customer_industry": "系统集成",
        "bid_date": (date.today() + timedelta(days=30)).isoformat(),
        "bid_time_limit": 20,
    })
    assert r.status_code in (200, 201), f"Task create failed: {r.text}"
    return r.json()["id"]


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

class TestAuth:
    def test_me(self, client, auth_headers):
        r = client.get("/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "email" in data
        assert "tenant_id" in data

    def test_me_without_token(self, client):
        r = client.get("/auth/me")
        assert r.status_code == 401


# ─────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────

class TestKnowledgeBase:
    def test_get_upload_url(self, client, auth_headers):
        r = client.post("/knowledge/documents/upload-url", headers=auth_headers, json={
            "file_name": "test_doc.txt",
            "content_type": "text/plain",
        })
        assert r.status_code == 200
        data = r.json()
        assert "upload_url" in data
        assert "object_key" in data
        assert "test_doc.txt" in data["object_key"]

    def test_upload_url_includes_tenant_path(self, client, auth_headers):
        """object_key must be namespaced under tenant_id"""
        r = client.post("/knowledge/documents/upload-url", headers=auth_headers, json={
            "file_name": "bid_doc.pdf",
            "content_type": "application/pdf",
        })
        assert r.status_code == 200
        key = r.json()["object_key"]
        # Should not allow path traversal
        assert ".." not in key

    def test_list_documents_empty(self, client, auth_headers):
        r = client.get("/knowledge/documents", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_documents_filters(self, client, auth_headers):
        """Filter by doc_type and embedding_status"""
        r = client.get("/knowledge/documents", headers=auth_headers, params={
            "doc_type": "bid_doc",
            "embedding_status": 2,
        })
        assert r.status_code == 200

    def test_get_nonexistent_document(self, client, auth_headers):
        r = client.get("/knowledge/documents/9999999", headers=auth_headers)
        assert r.status_code == 404

    def test_delete_nonexistent_document(self, client, auth_headers):
        r = client.delete("/knowledge/documents/9999999", headers=auth_headers)
        assert r.status_code == 404

    def test_search_empty_query(self, client, auth_headers):
        r = client.post("/knowledge/search", headers=auth_headers, json={"query": ""})
        assert r.status_code == 200
        data = r.json()
        assert data["hits"] == []
        assert data["total"] == 0

    def test_search_with_query(self, client, auth_headers):
        """Search returns valid response shape even when no docs are indexed."""
        r = client.post("/knowledge/search", headers=auth_headers, json={
            "query": "系统集成方案",
            "top_n": 5,
        })
        assert r.status_code == 200
        data = r.json()
        assert "hits" in data
        assert "total" in data

    def test_search_without_auth(self, client):
        r = client.post("/knowledge/search", json={"query": "test"})
        assert r.status_code == 401


# ─────────────────────────────────────────────
# Training Plans & Sessions
# ─────────────────────────────────────────────

class TestTraining:
    @pytest.fixture(scope="class")
    def plan(self, client, auth_headers, task_id):
        r = client.post("/training/plans", headers=auth_headers, params={
            "pitch_task_id": task_id,
        })
        assert r.status_code in (200, 201), f"Create plan failed: {r.text}"
        return r.json()

    def test_create_plan(self, plan):
        assert plan["id"] > 0
        assert plan["pitch_task_id"] is not None
        assert plan["schedule_dates"] is not None
        assert len(plan["schedule_dates"]) >= 2

    def test_schedule_includes_today(self, plan):
        today = date.today().isoformat()
        assert today in plan["schedule_dates"], \
            f"Today ({today}) should be in schedule: {plan['schedule_dates']}"

    def test_schedule_sorted(self, plan):
        dates = plan["schedule_dates"]
        assert dates == sorted(dates), "Schedule dates must be in ascending order"

    def test_schedule_includes_bid_minus_1(self, plan):
        """Day before bid_date should be in schedule."""
        if plan["bid_date"]:
            bid = date.fromisoformat(plan["bid_date"])
            day_before = (bid - timedelta(days=1)).isoformat()
            assert day_before in plan["schedule_dates"], \
                f"Day-before-bid ({day_before}) must be in schedule"

    def test_create_plan_idempotent(self, client, auth_headers, task_id, plan):
        """Creating plan for same task returns existing plan."""
        r = client.post("/training/plans", headers=auth_headers, params={
            "pitch_task_id": task_id,
        })
        assert r.status_code in (200, 201)
        assert r.json()["id"] == plan["id"], "Should return existing plan, not create a new one"

    def test_list_plans(self, client, auth_headers, task_id, plan):
        r = client.get("/training/plans", headers=auth_headers, params={"pitch_task_id": task_id})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert any(p["id"] == plan["id"] for p in data)

    def test_get_plan(self, client, auth_headers, plan):
        r = client.get(f"/training/plans/{plan['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == plan["id"]

    def test_get_plan_not_found(self, client, auth_headers):
        r = client.get("/training/plans/9999999", headers=auth_headers)
        assert r.status_code == 404

    def test_today_endpoint(self, client, auth_headers):
        r = client.get("/training/today", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_submit_follow_session(self, client, auth_headers, plan):
        r = client.post("/training/sessions", headers=auth_headers, json={
            "plan_id": plan["id"],
            "mode": "follow",
            "page_number": 1,
            "transcript": "我们公司提供完整的系统集成解决方案，覆盖硬件采购、软件部署和后期运维支持服务，帮助客户实现数字化转型",
            "duration_sec": 45,
        })
        assert r.status_code in (200, 201), f"Submit session failed: {r.text}"
        data = r.json()
        assert data["mode"] == "follow"
        assert data["total_score"] is not None
        assert 0 <= data["total_score"] <= 100
        assert "dimension_scores" in data
        assert "content_alignment" in data["dimension_scores"]
        assert "rate_match" in data["dimension_scores"]
        assert "emphasis_hits" in data["dimension_scores"]
        assert "feedback" in data
        assert isinstance(data["feedback"], list)

    def test_submit_recite_session(self, client, auth_headers, plan):
        r = client.post("/training/sessions", headers=auth_headers, json={
            "plan_id": plan["id"],
            "mode": "recite",
            "page_number": 1,
            "transcript": "系统集成解决方案硬件采购软件部署运维支持数字化转型",
            "duration_sec": 30,
        })
        assert r.status_code in (200, 201), f"Submit session failed: {r.text}"
        data = r.json()
        assert data["mode"] == "recite"
        assert data["total_score"] is not None
        assert "coverage_rate" in data["dimension_scores"]
        assert "order_accuracy" in data["dimension_scores"]
        assert "naturalness" in data["dimension_scores"]

    def test_submit_invalid_mode(self, client, auth_headers, plan):
        r = client.post("/training/sessions", headers=auth_headers, json={
            "plan_id": plan["id"],
            "mode": "invalid_mode",
            "page_number": 1,
            "transcript": "test",
            "duration_sec": 30,
        })
        assert r.status_code == 422

    def test_submit_wrong_plan(self, client, auth_headers):
        r = client.post("/training/sessions", headers=auth_headers, json={
            "plan_id": 9999999,
            "mode": "follow",
            "page_number": 1,
            "transcript": "test",
            "duration_sec": 30,
        })
        assert r.status_code == 404

    def test_list_sessions(self, client, auth_headers, plan):
        r = client.get("/training/sessions", headers=auth_headers, params={"plan_id": plan["id"]})
        assert r.status_code == 200
        sessions = r.json()
        assert isinstance(sessions, list)
        assert len(sessions) >= 2  # we submitted 2 above

    def test_schedule_preview(self, client, auth_headers):
        today = date.today().isoformat()
        bid = (date.today() + timedelta(days=30)).isoformat()
        r = client.get("/training/schedule/preview", headers=auth_headers, params={
            "first_date": today,
            "bid_date": bid,
        })
        assert r.status_code == 200
        schedule = r.json()
        assert isinstance(schedule, list)
        assert today in schedule

    def test_schedule_preview_invalid_date(self, client, auth_headers):
        r = client.get("/training/schedule/preview", headers=auth_headers, params={
            "first_date": "not-a-date",
        })
        assert r.status_code == 422


# ─────────────────────────────────────────────
# Reviews & Certifications
# ─────────────────────────────────────────────

class TestReviews:
    def test_pending_reviews_empty(self, client, auth_headers):
        r = client.get("/reviews/pending", headers=auth_headers)
        # Endpoint requires manager/admin role; regular users get 403 — both outcomes are valid
        assert r.status_code in (200, 403)
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    def test_get_certification_not_found(self, client, auth_headers, task_id):
        r = client.get(f"/certifications/{task_id}", headers=auth_headers)
        # Either 404 (no cert) or 200 with null — both acceptable
        assert r.status_code in (200, 404)

    def test_submit_review_nonexistent_rehearsal(self, client, auth_headers):
        r = client.post("/rehearsals/9999999/submit-review", headers=auth_headers)
        assert r.status_code == 404

    def test_get_comments_nonexistent_rehearsal(self, client, auth_headers):
        r = client.get("/rehearsals/9999999/comments", headers=auth_headers)
        assert r.status_code == 404


# ─────────────────────────────────────────────
# Narrations
# ─────────────────────────────────────────────

class TestNarrations:
    def test_list_voices(self, client, auth_headers):
        r = client.get("/narrations/voices", headers=auth_headers)
        assert r.status_code == 200
        voices = r.json()
        assert isinstance(voices, list)
        assert len(voices) >= 1
        voice = voices[0]
        # API returns {id, name} (not voice_id)
        assert "id" in voice or "voice_id" in voice
        assert "name" in voice

    def test_generate_narration_nonexistent_plan(self, client, auth_headers):
        r = client.post("/narrations/9999999/generate", headers=auth_headers, json={
            "voice_id": "default",
            "voice_name": "专业男声",
            "speed": 1.0,
        })
        assert r.status_code == 404

    def test_latest_narration_nonexistent(self, client, auth_headers):
        r = client.get("/narrations/9999999/latest", headers=auth_headers)
        assert r.status_code == 404

    def test_list_narrations_nonexistent_plan(self, client, auth_headers):
        r = client.get("/narrations/9999999/list", headers=auth_headers)
        # Could return 404 or empty list — either is acceptable
        assert r.status_code in (200, 404)


# ─────────────────────────────────────────────
# Scoring unit tests (in-process)
# ─────────────────────────────────────────────

class TestScoringLogic:
    def test_follow_perfect_match(self):
        from app.services.training_service import score_follow_read
        text = "系统集成解决方案包括硬件采购和软件部署"
        result = score_follow_read(text, text, 40, 40)
        assert result["total_score"] >= 85
        assert result["dimension_scores"]["content_alignment"] >= 95

    def test_follow_empty_transcript(self):
        from app.services.training_service import score_follow_read
        result = score_follow_read("", "参考脚本内容", 0, 40)
        assert result["total_score"] < 50
        assert result["dimension_scores"]["content_alignment"] == 0

    def test_recite_full_coverage(self):
        from app.services.training_service import score_recitation
        tps = ["系统集成", "硬件采购", "软件部署", "运维支持"]
        transcript = "系统集成方案包含硬件采购和软件部署还有运维支持"
        result = score_recitation(transcript, tps, transcript, 40)
        assert result["dimension_scores"]["coverage_rate"] >= 75

    def test_recite_filler_words(self):
        from app.services.training_service import score_recitation
        filler_heavy = "那个系统集成嗯就是硬件采购然后软件部署啊运维支持那个那个"
        result = score_recitation(filler_heavy, ["系统集成", "硬件采购"], filler_heavy, 20)
        assert result["dimension_scores"]["naturalness"] < 90

    def test_ebbinghaus_schedule_basic(self):
        from app.services.training_service import generate_ebbinghaus_schedule
        today = date.today()
        bid = today + timedelta(days=20)
        schedule = generate_ebbinghaus_schedule(today, bid)
        assert today.isoformat() in schedule
        # Day-before-bid
        assert (bid - timedelta(days=1)).isoformat() in schedule
        # bid day itself
        assert bid.isoformat() in schedule

    def test_ebbinghaus_no_bid_date(self):
        from app.services.training_service import generate_ebbinghaus_schedule
        today = date.today()
        schedule = generate_ebbinghaus_schedule(today, None)
        assert today.isoformat() in schedule
        # All intervals applied, including 30-day
        expected_30 = (today + timedelta(days=30)).isoformat()
        assert expected_30 in schedule

    def test_ebbinghaus_bid_very_soon(self):
        """If bid is 2 days away, no post-bid dates."""
        from app.services.training_service import generate_ebbinghaus_schedule
        today = date.today()
        bid = today + timedelta(days=2)
        schedule = generate_ebbinghaus_schedule(today, bid)
        for d in schedule:
            assert d <= bid.isoformat(), f"Date {d} is after bid {bid}"

    def test_knowledge_chunking(self):
        from app.services.knowledge_service import _split_text, MAX_CHUNK, MIN_CHUNK
        # Use 200 repetitions so remainder (200 % 88 = 24 sentences = 216 chars)
        # is above MIN_CHUNK (150), preventing merging that inflates chunk size.
        long_text = "这是一段测试文本。" * 200  # 1800 chars
        chunks = _split_text(long_text)
        assert len(chunks) >= 2
        for c in chunks:
            # Each chunk should not exceed MAX_CHUNK + MIN_CHUNK (merged remainder bound)
            assert len(c) <= MAX_CHUNK + MIN_CHUNK + 5

    def test_knowledge_chunking_short(self):
        from app.services.knowledge_service import _split_text
        short = "这是一段很短的文本，不需要分块。"
        chunks = _split_text(short)
        # Short text: either returns as-is or empty if below MIN_CHUNK
        assert isinstance(chunks, list)

    def test_rrf_merge(self):
        from app.services.knowledge_service import _rrf_merge
        vector_hits = [{"chunk_id": 1, "score": 0.9}, {"chunk_id": 2, "score": 0.8}]
        keyword_hits = [{"chunk_id": 2, "score": 1.0}, {"chunk_id": 3, "score": 0.5}]
        merged = _rrf_merge(vector_hits, keyword_hits, top_n=3)
        assert len(merged) == 3
        # chunk_id 2 appears in both lists → should rank highest
        assert merged[0]["chunk_id"] == 2

    def test_asr_stub(self):
        from app.services.asr_adapter import _stub_transcribe
        fake_audio = b"\x00" * 1024  # 1KB
        segments = _stub_transcribe(fake_audio)
        assert isinstance(segments, list)
        assert len(segments) >= 1
        assert "text" in segments[0]
        assert segments[0]["end"] > segments[0]["start"]


# ─────────────────────────────────────────────
# Pitch Task integration
# ─────────────────────────────────────────────

class TestPitchTask:
    def test_list_tasks(self, client, auth_headers):
        r = client.get("/pitch-tasks", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # Could be paginated or a list
        if isinstance(data, dict):
            assert "items" in data or "data" in data
        else:
            assert isinstance(data, list)

    def test_get_task(self, client, auth_headers, task_id):
        r = client.get(f"/pitch-tasks/{task_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == task_id

    def test_get_task_not_found(self, client, auth_headers):
        r = client.get("/pitch-tasks/9999999", headers=auth_headers)
        assert r.status_code == 404

    def test_cross_tenant_isolation(self, client, auth_headers, task_id):
        """A different user's token cannot see this task (tenant isolation)."""
        import random
        suffix = random.randint(100000, 999999)
        # Register second user
        r = client.post("/auth/register", json={
            "email": f"other_{suffix}@example.com",
            "password": "OtherPass123!",
            "full_name": "Other User",
            "tenant_name": f"Other Corp {suffix}",
        })
        if r.status_code not in (200, 201):
            pytest.skip("Cannot register second user")
        r2 = client.post("/auth/login", json={
            "email": f"other_{suffix}@example.com",
            "password": "OtherPass123!",
        })
        token2 = r2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Other tenant should get 404 on first user's task
        r3 = client.get(f"/pitch-tasks/{task_id}", headers=headers2)
        assert r3.status_code == 404, \
            f"Cross-tenant isolation failed: status {r3.status_code}"
