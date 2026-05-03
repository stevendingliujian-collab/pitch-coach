#!/usr/bin/env python3
"""
Standalone E2E test runner for P1 features.
No pytest required — just httpx (already in requirements.txt).

Usage:
    cd backend
    source .venv/bin/activate
    python tests/run_e2e.py
"""
import sys
import traceback
import random
import json
from datetime import date, timedelta

try:
    import httpx
except ImportError:
    print("❌ httpx not installed. Run: pip install httpx")
    sys.exit(1)

BASE = "http://localhost:8001/api/v1"
client = httpx.Client(base_url=BASE, timeout=30)

PASS = 0
FAIL = 0
ERRORS = []


def test(name: str, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  ✅  {name}")
        PASS += 1
    except AssertionError as e:
        print(f"  ❌  {name}: {e}")
        FAIL += 1
        ERRORS.append((name, str(e)))
    except Exception as e:
        print(f"  💥  {name}: {type(e).__name__}: {e}")
        FAIL += 1
        ERRORS.append((name, traceback.format_exc(limit=3)))


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ─────────────────────────────────────────────────────────────
# Setup: register + login
# ─────────────────────────────────────────────────────────────

suffix = random.randint(10000, 99999)
EMAIL = f"e2e_{suffix}@example.com"    # use .com — .test fails email validation
PASSWORD = "TestPass123!"
TOKEN = None
HEADERS = {}
TASK_ID = None
PLAN_ID = None  # training plan id
PITCH_PLAN_ID = None

section("🔑  Setup: Register & Login")

def setup_register():
    r = client.post("/auth/register", json={
        "email": EMAIL,
        "password": PASSWORD,
        "name": "E2E Tester",            # field is 'name', not 'full_name'
        "company_name": f"E2E Corp {suffix}",   # field is 'company_name'
    })
    assert r.status_code in (200, 201), f"Register failed {r.status_code}: {r.text}"

def setup_login():
    global TOKEN, HEADERS
    r = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})  # 'email' not 'username'
    assert r.status_code == 200, f"Login failed {r.status_code}: {r.text}"
    TOKEN = r.json()["access_token"]
    HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def setup_me():
    r = client.get("/auth/me", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "email" in data and "tenant_id" in data

def setup_create_task():
    global TASK_ID
    r = client.post("/pitch-tasks", headers=HEADERS, json={
        "name": "E2E 述标测试项目",
        "customer_name": "测试客户",
        "customer_industry": "系统集成",
        "bid_date": (date.today() + timedelta(days=30)).isoformat(),
        "bid_time_limit": 20,
    })
    assert r.status_code in (200, 201), f"Task create failed {r.status_code}: {r.text}"
    TASK_ID = r.json()["id"]
    assert TASK_ID > 0

test("Register user", setup_register)
test("Login & get token", setup_login)
test("GET /auth/me", setup_me)
test("Create pitch task", setup_create_task)

if not TOKEN:
    print("\n❌  Cannot continue without auth token. Aborting.")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Auth edge cases
# ─────────────────────────────────────────────────────────────

section("🔒  Auth")

def auth_unauth():
    r = client.get("/auth/me")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
test("Unauthenticated /me returns 401", auth_unauth)

def auth_bad_token():
    r = client.get("/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
test("Invalid token returns 401", auth_bad_token)


# ─────────────────────────────────────────────────────────────
# Knowledge Base
# ─────────────────────────────────────────────────────────────

section("📚  Knowledge Base")

def kb_upload_url():
    r = client.post("/knowledge/documents/upload-url", headers=HEADERS, json={
        "file_name": "test_bid.pdf",
        "content_type": "application/pdf",
    })
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    data = r.json()
    assert "upload_url" in data
    assert "object_key" in data
    assert "test_bid.pdf" in data["object_key"]
    assert ".." not in data["object_key"]   # no path traversal
test("GET upload presigned URL", kb_upload_url)

def kb_upload_url_sanitise():
    """Path traversal in filename must be sanitised"""
    r = client.post("/knowledge/documents/upload-url", headers=HEADERS, json={
        "file_name": "../../etc/passwd",
        "content_type": "text/plain",
    })
    assert r.status_code == 200
    assert ".." not in r.json()["object_key"]
test("Upload URL sanitises path traversal in filename", kb_upload_url_sanitise)

def kb_list_empty():
    r = client.get("/knowledge/documents", headers=HEADERS)
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
test("List documents (empty)", kb_list_empty)

def kb_list_filters():
    r = client.get("/knowledge/documents", headers=HEADERS, params={
        "doc_type": "bid_doc",
        "embedding_status": 0,
        "page": 1,
        "page_size": 10,
    })
    assert r.status_code == 200
test("List documents with filters", kb_list_filters)

def kb_get_404():
    r = client.get("/knowledge/documents/9999999", headers=HEADERS)
    assert r.status_code == 404
test("GET nonexistent document returns 404", kb_get_404)

def kb_delete_404():
    r = client.delete("/knowledge/documents/9999999", headers=HEADERS)
    assert r.status_code == 404
test("DELETE nonexistent document returns 404", kb_delete_404)

def kb_search_empty_query():
    r = client.post("/knowledge/search", headers=HEADERS, json={"query": ""})
    assert r.status_code == 200
    data = r.json()
    assert data["hits"] == []
    assert data["total"] == 0
test("Search with empty query returns empty hits", kb_search_empty_query)

def kb_search_no_docs():
    r = client.post("/knowledge/search", headers=HEADERS, json={
        "query": "系统集成述标方案",
        "top_n": 5,
    })
    assert r.status_code == 200
    data = r.json()
    assert "hits" in data
    assert "total" in data
    assert isinstance(data["hits"], list)
test("Search with query returns valid shape", kb_search_no_docs)

def kb_search_unauth():
    r = client.post("/knowledge/search", json={"query": "test"})
    assert r.status_code == 401
test("Search without auth returns 401", kb_search_unauth)

def kb_search_doc_type_filter():
    r = client.post("/knowledge/search", headers=HEADERS, json={
        "query": "系统集成",
        "doc_type": "bid_doc",
        "top_n": 3,
    })
    assert r.status_code == 200
test("Search with doc_type filter", kb_search_doc_type_filter)


# ─────────────────────────────────────────────────────────────
# Training Plans
# ─────────────────────────────────────────────────────────────

section("🏋️  Training Plans")

training_plan = None

def tp_create():
    global training_plan, PLAN_ID
    r = client.post("/training/plans", headers=HEADERS, params={
        "pitch_task_id": TASK_ID,
    })
    assert r.status_code in (200, 201), f"{r.status_code}: {r.text}"
    data = r.json()
    assert data["id"] > 0
    assert data["pitch_task_id"] == TASK_ID
    assert isinstance(data["schedule_dates"], list)
    assert len(data["schedule_dates"]) >= 2
    training_plan = data
    PLAN_ID = data["id"]
test("Create training plan", tp_create)

def tp_schedule_today():
    assert training_plan is not None
    today = date.today().isoformat()
    assert today in training_plan["schedule_dates"], \
        f"Today {today} not in schedule: {training_plan['schedule_dates']}"
test("Schedule includes today (first_practice_date)", tp_schedule_today)

def tp_schedule_sorted():
    assert training_plan is not None
    dates = training_plan["schedule_dates"]
    assert dates == sorted(dates), f"Dates not sorted: {dates}"
test("Schedule dates are sorted", tp_schedule_sorted)

def tp_schedule_day_before_bid():
    assert training_plan is not None
    if training_plan.get("bid_date"):
        bid = date.fromisoformat(training_plan["bid_date"])
        day_before = (bid - timedelta(days=1)).isoformat()
        assert day_before in training_plan["schedule_dates"], \
            f"Day-before-bid {day_before} not in {training_plan['schedule_dates']}"
test("Schedule includes day before bid", tp_schedule_day_before_bid)

def tp_idempotent():
    global training_plan
    r = client.post("/training/plans", headers=HEADERS, params={"pitch_task_id": TASK_ID})
    assert r.status_code in (200, 201)
    assert r.json()["id"] == PLAN_ID, "Should return existing plan"
test("Create plan is idempotent", tp_idempotent)

def tp_list():
    r = client.get("/training/plans", headers=HEADERS, params={"pitch_task_id": TASK_ID})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(p["id"] == PLAN_ID for p in data)
test("List plans by task_id", tp_list)

def tp_get():
    r = client.get(f"/training/plans/{PLAN_ID}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["id"] == PLAN_ID
test("GET plan by id", tp_get)

def tp_get_404():
    r = client.get("/training/plans/9999999", headers=HEADERS)
    assert r.status_code == 404
test("GET nonexistent plan returns 404", tp_get_404)

def tp_today():
    r = client.get("/training/today", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # our plan has today scheduled, so it should appear
    assert any(item["plan_id"] == PLAN_ID for item in data), \
        f"Plan {PLAN_ID} not in today's list: {data}"
test("Today endpoint includes our new plan", tp_today)

def tp_schedule_preview():
    today = date.today().isoformat()
    bid = (date.today() + timedelta(days=20)).isoformat()
    r = client.get("/training/schedule/preview", headers=HEADERS, params={
        "first_date": today,
        "bid_date": bid,
    })
    assert r.status_code == 200
    schedule = r.json()
    assert today in schedule
    # Day 1 interval
    assert (date.today() + timedelta(days=1)).isoformat() in schedule
test("Schedule preview endpoint", tp_schedule_preview)

def tp_schedule_preview_bad_date():
    r = client.get("/training/schedule/preview", headers=HEADERS, params={
        "first_date": "not-a-date",
    })
    assert r.status_code == 422
test("Schedule preview with invalid date returns 422", tp_schedule_preview_bad_date)


# ─────────────────────────────────────────────────────────────
# Training Sessions
# ─────────────────────────────────────────────────────────────

section("🎙️  Training Sessions")

follow_session = None
recite_session = None

def ts_submit_follow():
    global follow_session
    r = client.post("/training/sessions", headers=HEADERS, json={
        "plan_id": PLAN_ID,
        "mode": "follow",
        "page_number": 1,
        "transcript": "我们公司提供完整的系统集成解决方案，覆盖硬件采购、软件部署和后期运维支持服务，帮助客户实现数字化转型目标",
        "duration_sec": 45,
    })
    assert r.status_code in (200, 201), f"{r.status_code}: {r.text}"
    data = r.json()
    assert data["mode"] == "follow"
    assert data["page_number"] == 1
    assert data["total_score"] is not None
    assert 0 <= data["total_score"] <= 100
    assert data["dimension_scores"] is not None
    assert "content_alignment" in data["dimension_scores"]
    assert "rate_match" in data["dimension_scores"]
    assert "emphasis_hits" in data["dimension_scores"]
    assert isinstance(data["feedback"], list)
    assert len(data["feedback"]) >= 1
    follow_session = data
test("Submit follow-read session", ts_submit_follow)

def ts_follow_score_range():
    assert follow_session is not None
    for key, val in follow_session["dimension_scores"].items():
        assert 0 <= val <= 100, f"{key}={val} out of [0,100]"
test("Follow-read dimension scores in [0,100]", ts_follow_score_range)

def ts_submit_recite():
    global recite_session
    r = client.post("/training/sessions", headers=HEADERS, json={
        "plan_id": PLAN_ID,
        "mode": "recite",
        "page_number": 1,
        "transcript": "系统集成解决方案包括硬件采购软件部署运维支持数字化转型",
        "duration_sec": 30,
    })
    assert r.status_code in (200, 201), f"{r.status_code}: {r.text}"
    data = r.json()
    assert data["mode"] == "recite"
    assert "coverage_rate" in data["dimension_scores"]
    assert "order_accuracy" in data["dimension_scores"]
    assert "naturalness" in data["dimension_scores"]
    recite_session = data
test("Submit recite session", ts_submit_recite)

def ts_recite_score_range():
    assert recite_session is not None
    for key, val in recite_session["dimension_scores"].items():
        assert 0 <= val <= 100, f"{key}={val} out of [0,100]"
test("Recite dimension scores in [0,100]", ts_recite_score_range)

def ts_invalid_mode():
    r = client.post("/training/sessions", headers=HEADERS, json={
        "plan_id": PLAN_ID,
        "mode": "invalid_xyz",
        "page_number": 1,
        "transcript": "test",
        "duration_sec": 30,
    })
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
test("Submit session with invalid mode returns 422", ts_invalid_mode)

def ts_wrong_plan():
    r = client.post("/training/sessions", headers=HEADERS, json={
        "plan_id": 9999999,
        "mode": "follow",
        "page_number": 1,
        "transcript": "test",
        "duration_sec": 30,
    })
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
test("Submit session for nonexistent plan returns 404", ts_wrong_plan)

def ts_list():
    r = client.get("/training/sessions", headers=HEADERS, params={"plan_id": PLAN_ID})
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 2  # submitted follow + recite above
    ids = [s["id"] for s in sessions]
    assert follow_session["id"] in ids
    assert recite_session["id"] in ids
test("List sessions returns submitted sessions", ts_list)

def ts_no_auth():
    r = client.post("/training/sessions", json={
        "plan_id": PLAN_ID, "mode": "follow",
        "page_number": 1, "transcript": "test", "duration_sec": 10,
    })
    assert r.status_code == 401
test("Submit session without auth returns 401", ts_no_auth)


# ─────────────────────────────────────────────────────────────
# Reviews & Certifications
# ─────────────────────────────────────────────────────────────

section("📋  Reviews & Certifications")

def rev_pending_list():
    """Regular users (role=member) should get 403; only managers/admins can access."""
    r = client.get("/reviews/pending", headers=HEADERS)
    assert r.status_code == 403, f"Expected 403 for non-manager user, got {r.status_code}: {r.text}"
    assert "manager" in r.json().get("detail", "").lower()
test("GET pending reviews (non-manager) returns 403", rev_pending_list)

def rev_cert_not_found():
    r = client.get(f"/certifications/{TASK_ID}", headers=HEADERS)
    assert r.status_code in (200, 404), f"Unexpected {r.status_code}"
test("GET cert for task without cert", rev_cert_not_found)

def rev_submit_nonexistent():
    r = client.post("/rehearsals/9999999/submit-review", headers=HEADERS)
    assert r.status_code == 404
test("Submit review for nonexistent rehearsal returns 404", rev_submit_nonexistent)

def rev_comments_nonexistent():
    r = client.get("/rehearsals/9999999/comments", headers=HEADERS)
    assert r.status_code == 404
test("GET comments for nonexistent rehearsal returns 404", rev_comments_nonexistent)

def rev_unauth_pending():
    r = client.get("/reviews/pending")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
test("Pending reviews without auth returns 401", rev_unauth_pending)


# ─────────────────────────────────────────────────────────────
# Narrations
# ─────────────────────────────────────────────────────────────

section("🎧  Narrations")

def narr_voices():
    r = client.get("/narrations/voices", headers=HEADERS)
    assert r.status_code == 200
    voices = r.json()
    assert isinstance(voices, list)
    assert len(voices) >= 1
    v = voices[0]
    assert "id" in v or "voice_id" in v, f"Voice has no id key: {v}"
    assert "name" in v
test("List voices returns presets", narr_voices)

def narr_generate_404():
    r = client.post("/narrations/9999999/generate", headers=HEADERS, json={
        "voice_id": "default",
        "voice_name": "专业男声",
        "speed": 1.0,
    })
    assert r.status_code == 404
test("Generate narration for nonexistent plan returns 404", narr_generate_404)

def narr_latest_404():
    r = client.get("/narrations/9999999/latest", headers=HEADERS)
    assert r.status_code == 404
test("GET latest narration for nonexistent plan returns 404", narr_latest_404)

def narr_unauth():
    r = client.get("/narrations/voices")
    assert r.status_code == 401
test("Narrations without auth returns 401", narr_unauth)


# ─────────────────────────────────────────────────────────────
# In-process unit tests (no HTTP)
# ─────────────────────────────────────────────────────────────

section("🧪  Unit Tests (scoring & scheduling)")

def unit_follow_perfect():
    import sys; sys.path.insert(0, ".")
    from app.services.training_service import score_follow_read
    text = "系统集成解决方案包括硬件采购和软件部署"
    result = score_follow_read(text, text, 40, 40)
    assert result["total_score"] >= 85, f"Perfect match score: {result['total_score']}"
    assert result["dimension_scores"]["content_alignment"] >= 95
test("Follow-read: perfect match scores ≥85", unit_follow_perfect)

def unit_follow_empty():
    from app.services.training_service import score_follow_read
    result = score_follow_read("", "参考脚本内容系统集成", 0, 40)
    assert result["total_score"] < 50
    assert result["dimension_scores"]["content_alignment"] == 0
test("Follow-read: empty transcript scores <50", unit_follow_empty)

def unit_follow_score_bounds():
    from app.services.training_service import score_follow_read
    for transcript, ref in [
        ("", "ref"),
        ("identical", "identical"),
        ("完全不同的内容与任何参考均无关联", "系统集成硬件软件部署"),
    ]:
        result = score_follow_read(transcript, ref, 40, 40)
        score = result["total_score"]
        assert 0 <= score <= 100, f"Score {score} out of bounds for '{transcript[:20]}'"
test("Follow-read scores always in [0,100]", unit_follow_score_bounds)

def unit_recite_coverage():
    from app.services.training_service import score_recitation
    tps = ["系统集成", "硬件采购", "软件部署", "运维支持"]
    transcript = "我们的系统集成方案含硬件采购和软件部署还有运维支持"
    result = score_recitation(transcript, tps, transcript, 40)
    assert result["dimension_scores"]["coverage_rate"] >= 75
test("Recite: full coverage ≥75", unit_recite_coverage)

def unit_recite_filler():
    from app.services.training_service import score_recitation
    filler = "那个系统集成嗯就是那个硬件采购然后那个软件部署啊啊那个运维那个那个那个"
    result = score_recitation(filler, ["系统集成"], filler, 20)
    assert result["dimension_scores"]["naturalness"] < 90
test("Recite: heavy filler words reduce naturalness", unit_recite_filler)

def unit_recite_bounds():
    from app.services.training_service import score_recitation
    for transcript in ["", "系统集成硬件软件", "那个嗯啊那个那个嗯那个"]:
        result = score_recitation(transcript, ["系统集成"], "参考", 30)
        assert 0 <= result["total_score"] <= 100
test("Recite scores always in [0,100]", unit_recite_bounds)

def unit_ebbinghaus_basic():
    from app.services.training_service import generate_ebbinghaus_schedule
    today = date.today()
    bid = today + timedelta(days=20)
    schedule = generate_ebbinghaus_schedule(today, bid)
    assert today.isoformat() in schedule
    assert (bid - timedelta(days=1)).isoformat() in schedule
    assert bid.isoformat() in schedule
    assert schedule == sorted(schedule)
test("Ebbinghaus: basic schedule correctness", unit_ebbinghaus_basic)

def unit_ebbinghaus_no_bid():
    from app.services.training_service import generate_ebbinghaus_schedule
    today = date.today()
    schedule = generate_ebbinghaus_schedule(today, None)
    assert today.isoformat() in schedule
    assert (today + timedelta(days=30)).isoformat() in schedule
test("Ebbinghaus: no bid date includes 30-day interval", unit_ebbinghaus_no_bid)

def unit_ebbinghaus_near_bid():
    from app.services.training_service import generate_ebbinghaus_schedule
    today = date.today()
    bid = today + timedelta(days=2)
    schedule = generate_ebbinghaus_schedule(today, bid)
    for d in schedule:
        assert d <= bid.isoformat(), f"Date {d} after bid {bid}"
test("Ebbinghaus: no dates after bid_date", unit_ebbinghaus_near_bid)

def unit_chunking_max_size():
    from app.services.knowledge_service import _split_text
    long_text = "这是一段测试文本用于验证分块算法。" * 60
    chunks = _split_text(long_text)
    assert len(chunks) >= 1
    for c in chunks:
        assert len(c) <= 900, f"Chunk too long: {len(c)} chars"
test("Knowledge chunking: max chunk size ≤900 chars", unit_chunking_max_size)

def unit_rrf_overlap():
    from app.services.knowledge_service import _rrf_merge
    vec = [{"chunk_id": 1, "score": 0.9, "content": "a"}, {"chunk_id": 2, "score": 0.8, "content": "b"}]
    kw  = [{"chunk_id": 2, "score": 1.0, "content": "b"}, {"chunk_id": 3, "score": 0.5, "content": "c"}]
    merged = _rrf_merge(vec, kw, top_n=3)
    assert len(merged) == 3
    assert merged[0]["chunk_id"] == 2, f"chunk_id 2 should rank first (in both lists), got {merged[0]['chunk_id']}"
test("RRF: item in both lists ranks highest", unit_rrf_overlap)

def unit_rrf_no_overlap():
    from app.services.knowledge_service import _rrf_merge
    vec = [{"chunk_id": 1, "score": 0.9, "content": "a"}]
    kw  = [{"chunk_id": 2, "score": 1.0, "content": "b"}]
    merged = _rrf_merge(vec, kw, top_n=2)
    assert len(merged) == 2
    ids = {m["chunk_id"] for m in merged}
    assert ids == {1, 2}
test("RRF: no-overlap returns both items", unit_rrf_no_overlap)

def unit_asr_stub():
    from app.services.asr_adapter import _stub_transcribe
    segs = _stub_transcribe(b"\x00" * 512)
    assert len(segs) >= 1
    assert "text" in segs[0]
    assert segs[0]["end"] > segs[0]["start"]
test("ASR stub returns valid segment shape", unit_asr_stub)

def unit_asr_format_detection():
    from app.services.asr_adapter import _detect_suffix
    assert _detect_suffix(b"ID3" + b"\x00" * 100) == ".mp3"
    assert _detect_suffix(b"RIFF" + b"\x00" * 100) == ".wav"
    assert _detect_suffix(b"fLaC" + b"\x00" * 100) == ".flac"
    assert _detect_suffix(b"OggS" + b"\x00" * 100) == ".ogg"
    assert _detect_suffix(b"\x00" * 100) == ".webm"  # default
test("ASR format detection by magic bytes", unit_asr_format_detection)


# ─────────────────────────────────────────────────────────────
# Tenant isolation
# ─────────────────────────────────────────────────────────────

section("🔐  Tenant Isolation")

def _register_and_login(email, password, name, company):
    r = client.post("/auth/register", json={
        "email": email, "password": password,
        "name": name, "company_name": company,
    })
    if r.status_code not in (200, 201):
        raise AssertionError(f"Cannot register {email}: {r.text}")
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200, f"Login failed: {r2.text}"
    return {"Authorization": f"Bearer {r2.json()['access_token']}"}

def isolation_task():
    suffix2 = random.randint(100000, 999999)
    h2 = _register_and_login(
        f"other_{suffix2}@example.com", "OtherPass123!",
        "Other User", f"Other Corp {suffix2}",
    )
    r3 = client.get(f"/pitch-tasks/{TASK_ID}", headers=h2)
    assert r3.status_code == 404, f"Cross-tenant isolation FAILED: got {r3.status_code}"
test("Cross-tenant task isolation", isolation_task)

def isolation_training_plan():
    suffix3 = random.randint(100000, 999999)
    h3 = _register_and_login(
        f"other2_{suffix3}@example.com", "OtherPass123!",
        "Other2", f"Other Corp2 {suffix3}",
    )
    r3 = client.get(f"/training/plans/{PLAN_ID}", headers=h3)
    assert r3.status_code == 404, f"Training plan isolation FAILED: got {r3.status_code}"
test("Cross-tenant training plan isolation", isolation_training_plan)


# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────

section("📊  Summary")
total = PASS + FAIL
print(f"\n  Passed: {PASS}/{total}")
print(f"  Failed: {FAIL}/{total}")

if ERRORS:
    print("\n  Failed tests:")
    for name, err in ERRORS:
        print(f"    ❌  {name}")
        # Print first line of error
        first_line = err.split("\n")[0]
        print(f"       {first_line}")

print()
sys.exit(0 if FAIL == 0 else 1)
