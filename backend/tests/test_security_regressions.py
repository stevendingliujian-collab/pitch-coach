"""Regression tests for the PMF security hardening fixes.

These lock the highest-value fixes without needing a live DB / server:
  - role self-escalation whitelist (auth.py update_profile)
  - production SECRET_KEY guard (config.py)
  - ASR/TTS explicit failure instead of silent placeholder output

Run: pytest tests/test_security_regressions.py
"""
import importlib
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load_real(modname):
    """Return the real module, re-importing if another test left a stub
    (a bare ModuleType with no __file__) in sys.modules. Test files in this
    suite stub app.services.* into sys.modules; this defends against that
    pollution regardless of test execution order."""
    mod = sys.modules.get(modname)
    if mod is None or getattr(mod, "__file__", None) is None:
        sys.modules.pop(modname, None)
        mod = importlib.import_module(modname)
    return mod


# ── 1. Role self-escalation whitelist ─────────────────────────────────────────

from app.core.authz import (  # noqa: E402
    resolve_onboarding_role,
    InvalidRoleError,
    ONBOARDING_ROLES,
    PRIVILEGED_ROLES,
)


def test_member_can_set_allowed_job_role():
    assert resolve_onboarding_role("member", "pre_sales") == "pre_sales"


@pytest.mark.parametrize("privileged", ["admin", "manager", "owner"])
def test_escalation_to_privileged_role_is_rejected(privileged):
    # The RBAC roles are NOT in the allowed set → escalation attempt raises.
    with pytest.raises(InvalidRoleError):
        resolve_onboarding_role("member", privileged)


def test_arbitrary_role_string_is_rejected():
    with pytest.raises(InvalidRoleError):
        resolve_onboarding_role("member", "superadmin")


@pytest.mark.parametrize("privileged", ["owner", "admin", "manager"])
def test_privileged_user_is_not_downgraded(privileged):
    # An already-privileged account keeps its role (returns None = no change).
    assert resolve_onboarding_role(privileged, "pre_sales") is None


def test_privileged_and_onboarding_role_sets_are_disjoint():
    # Guards against someone accidentally adding an RBAC role to the job list.
    assert ONBOARDING_ROLES.isdisjoint(PRIVILEGED_ROLES)


# ── 2. Production SECRET_KEY guard ────────────────────────────────────────────

def _fresh_get_settings():
    """Import get_settings with its lru_cache cleared so env changes apply."""
    from app.core import config
    config.get_settings.cache_clear()
    return config.get_settings


def test_production_rejects_default_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
    get_settings = _fresh_get_settings()
    with pytest.raises(RuntimeError):
        get_settings()
    get_settings.cache_clear()


def test_production_accepts_real_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a-real-strong-secret-value-123456")
    get_settings = _fresh_get_settings()
    s = get_settings()
    assert s.is_production is True
    get_settings.cache_clear()


def test_development_allows_default_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
    get_settings = _fresh_get_settings()
    s = get_settings()
    assert s.is_production is False
    get_settings.cache_clear()


# ── 3. ASR/TTS explicit failure (no silent placeholder) ───────────────────────

def _settings_stub(**overrides):
    base = dict(
        asr_provider="paraformer",
        tts_provider="fish_audio",
        llm_api_key="",
        llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        embedding_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        fish_audio_api_key="",
        fish_audio_base_url="https://api.fish.audio/v1",
        xfyun_app_id="", xfyun_api_key="", xfyun_api_secret="",
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_asr_raises_when_key_missing(monkeypatch):
    asr_adapter = _load_real('app.services.asr_adapter')
    monkeypatch.setattr(asr_adapter, "get_settings", lambda: _settings_stub(), raising=False)
    # patch the module-level import target used inside transcribe()
    import app.core.config as config
    monkeypatch.setattr(config, "get_settings", lambda: _settings_stub())
    with pytest.raises(asr_adapter.AsrError):
        await asr_adapter.transcribe(b"\x00\x00fake-audio")


@pytest.mark.asyncio
async def test_asr_unknown_provider_raises(monkeypatch):
    asr_adapter = _load_real('app.services.asr_adapter')
    import app.core.config as config
    monkeypatch.setattr(config, "get_settings", lambda: _settings_stub(asr_provider="bogus"))
    with pytest.raises(asr_adapter.AsrError):
        await asr_adapter.transcribe(b"audio")


@pytest.mark.asyncio
async def test_asr_stub_provider_still_returns_placeholder(monkeypatch):
    # Explicit stub mode is the ONLY way to get placeholder text.
    asr_adapter = _load_real('app.services.asr_adapter')
    import app.core.config as config
    monkeypatch.setattr(config, "get_settings", lambda: _settings_stub(asr_provider="stub"))
    segments = await asr_adapter.transcribe(b"audio")
    assert segments and "占位" in segments[0]["text"]


@pytest.mark.asyncio
async def test_tts_raises_when_key_missing(monkeypatch):
    tts_adapter = _load_real('app.services.tts_adapter')
    import app.core.config as config
    monkeypatch.setattr(config, "get_settings", lambda: _settings_stub())
    with pytest.raises(tts_adapter.TtsError):
        await tts_adapter.text_to_speech("你好")


@pytest.mark.asyncio
async def test_tts_stub_provider_returns_silent_wav(monkeypatch):
    tts_adapter = _load_real('app.services.tts_adapter')
    import app.core.config as config
    monkeypatch.setattr(config, "get_settings", lambda: _settings_stub(tts_provider="stub"))
    audio = await tts_adapter.text_to_speech("你好")
    assert audio[:4] == b"RIFF"  # valid (silent) WAV header
