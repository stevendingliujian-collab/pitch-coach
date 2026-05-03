"""
TTS adapter — pluggable between Fish Audio, 科大讯飞 (iFlytek) WebAPI, and stub.

Provider selection via TTS_PROVIDER env / config:
  - "fish_audio"  →  Fish Audio S2 Pro (requires FISH_AUDIO_API_KEY)
  - "xfyun"       →  科大讯飞在线语音合成 WebAPI
                     (requires XFYUN_APP_ID + XFYUN_API_KEY + XFYUN_API_SECRET)
  - "stub"        →  Silent WAV placeholder (for testing)
"""
from __future__ import annotations

import logging
import struct
import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice presets: provider-specific.  The frontend uses display name → voice_id.
# For Fish Audio, voice_id is a UUID-like hash.
# For iFlytek, voice_id is a vcn code (e.g. "aisjiuxu").
# ---------------------------------------------------------------------------

# Fish Audio voice presets
_FISH_AUDIO_PRESETS: dict[str, str] = {
    "专业男声": "ad8d48dfaee44e1fa64a2e6f27448c60",
    "专业女声": "5a2403e41f5d4bc68d1bb5eb8b6cf52f",
    "商务男声": "54a5170264694bfc8e9ad98df7bd89c3",
    "温和女声": "e4642e5f-f4b1-4b80-8399-d1e71c9f8453",
}

# iFlytek voice presets (vcn codes) — standard + premium voices
_XFYUN_PRESETS: dict[str, str] = {
    "讯飞-标准男声": "aisjiuxu",
    "讯飞-标准女声": "xiaoyan",
    "讯飞-温柔女声": "x4_yezi",
    "讯飞-知性女声": "x4_lingxiaolu_oral",
    "讯飞-商务男声": "x4_mingge",
    "讯飞-磁性男声": "x4_lingbaolu",
}
_XFYUN_DEFAULT_VOICE = "aisjiuxu"


def _get_active_presets() -> dict[str, str]:
    """Return voice presets for the currently configured provider."""
    from app.core.config import get_settings
    provider = get_settings().tts_provider.lower()
    if provider == "xfyun":
        return _XFYUN_PRESETS
    return _FISH_AUDIO_PRESETS


# Module-level lazy attributes (provider-aware)
def __getattr__(name: str):
    if name == "VOICE_PRESETS":
        return _get_active_presets()
    if name == "DEFAULT_VOICE_ID":
        from app.core.config import get_settings
        provider = get_settings().tts_provider.lower()
        if provider == "xfyun":
            return _XFYUN_DEFAULT_VOICE
        return next(iter(_FISH_AUDIO_PRESETS.values()))
    raise AttributeError(name)


# Silence padding between pages (0.8 seconds)
PAGE_PAUSE_MS = 800


async def text_to_speech(
    text: str,
    voice_id: str | None = None,
    speed: float = 1.0,
    fmt: str = "mp3",
) -> bytes:
    """Convert text to speech. Returns raw audio bytes (MP3 or WAV)."""
    from app.core.config import get_settings
    settings = get_settings()

    provider = settings.tts_provider.lower()

    if provider == "fish_audio" and settings.fish_audio_api_key:
        return await _fish_audio_tts(
            text=text,
            voice_id=voice_id or next(iter(_FISH_AUDIO_PRESETS.values())),
            speed=speed,
            fmt=fmt,
            api_key=settings.fish_audio_api_key,
            base_url=settings.fish_audio_base_url,
        )

    if provider == "xfyun" and settings.xfyun_app_id and settings.xfyun_api_key and settings.xfyun_api_secret:
        return await _xfyun_tts(
            text=text,
            voice_id=voice_id or _XFYUN_DEFAULT_VOICE,
            speed=speed,
            app_id=settings.xfyun_app_id,
            api_key=settings.xfyun_api_key,
            api_secret=settings.xfyun_api_secret,
        )

    logger.warning("TTS_PROVIDER=%s or missing API credentials — using stub TTS", provider)
    return _stub_wav(max(1.0, len(text) / 200 * 3))


async def _fish_audio_tts(
    text: str,
    voice_id: str,
    speed: float,
    fmt: str,
    api_key: str,
    base_url: str,
) -> bytes:
    """Call Fish Audio TTS HTTP streaming endpoint and collect all bytes."""
    url = f"{base_url}/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "text": text,
        "reference_id": voice_id,
        "format": fmt,
        "normalize": True,
        "latency": "normal",
        "chunk_length": 200,
    }
    # Fish Audio doesn't support speed natively; we'll apply FFmpeg post-hoc
    # if speed != 1.0. For now, store the intent and handle in Celery task.

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            chunks: list[bytes] = []
            async for chunk in resp.aiter_bytes():
                if chunk:
                    chunks.append(chunk)
    return b"".join(chunks)


# ---------------------------------------------------------------------------
# iFlytek (科大讯飞) WebAPI TTS
# Doc: https://www.xfyun.cn/doc/tts/online_tts/API.html
# ---------------------------------------------------------------------------

async def _xfyun_tts(
    text: str,
    voice_id: str,
    speed: float,
    app_id: str,
    api_key: str,
    api_secret: str,
) -> bytes:
    """
    Call 科大讯飞 在线语音合成 WebAPI and return MP3 bytes.

    Auth: HMAC-SHA256 signature on (host + date + request-line).
    Response: JSON with base64-encoded audio chunks, or error status.
    """
    import base64
    import hashlib
    import hmac
    import json
    import time
    from datetime import datetime, timezone
    from email.utils import formatdate

    host = "tts-api.xfyun.cn"
    path = "/v2/tts"
    url = f"https://{host}{path}"

    # RFC1123 date
    date = formatdate(timeval=None, localtime=False, usegmt=True)

    # Build signature string
    signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature_b64 = base64.b64encode(signature_sha).decode("utf-8")

    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_b64}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
        "Date": date,
        "Host": host,
    }

    # Speed: iFlytek uses 0-100, default=50. Map our 0.75-1.5 to 0-100.
    # 0.75 → 25, 1.0 → 50, 1.5 → 100
    xf_speed = int((speed - 0.75) / (1.5 - 0.75) * 100)
    xf_speed = max(0, min(100, xf_speed))

    text_b64 = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    body = {
        "common": {"app_id": app_id},
        "business": {
            "aue": "lame",       # MP3
            "auf": "audio/L16;rate=16000",
            "vcn": voice_id,
            "speed": xf_speed,
            "volume": 70,
            "pitch": 50,
            "bgs": 0,
            "tte": "UTF8",
        },
        "data": {
            "status": 2,          # 2 = last frame (non-streaming mode)
            "text": text_b64,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            result = resp.json()

        code = result.get("code", -1)
        if code != 0:
            msg = result.get("message", "unknown error")
            logger.error("iFlytek TTS error code=%s msg=%s", code, msg)
            # Fallback to stub on API-level error
            return _stub_wav(max(1.0, len(text) / 200 * 3))

        # Collect audio: result["data"]["audio"] is base64 MP3
        audio_b64 = result.get("data", {}).get("audio", "")
        if not audio_b64:
            logger.error("iFlytek TTS: empty audio in response")
            return _stub_wav(max(1.0, len(text) / 200 * 3))

        return base64.b64decode(audio_b64)

    except httpx.HTTPStatusError as e:
        logger.error("iFlytek TTS HTTP error %s: %s", e.response.status_code, e.response.text[:200])
        return _stub_wav(max(1.0, len(text) / 200 * 3))
    except Exception as e:
        logger.error("iFlytek TTS failed: %s", e)
        return _stub_wav(max(1.0, len(text) / 200 * 3))


def _stub_wav(duration_sec: float = 2.0) -> bytes:
    """Generate a minimal silent WAV (for stub/test mode)."""
    sample_rate = 16000
    n_samples = int(sample_rate * duration_sec)
    data_size = n_samples * 2  # 16-bit mono
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1,
        sample_rate, sample_rate * 2,
        2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size
