"""TTS adapter — Fish Audio (primary) or stub."""
from __future__ import annotations

import logging
import struct
import httpx

logger = logging.getLogger(__name__)

# Public voice preset IDs on Fish Audio platform
VOICE_PRESETS: dict[str, str] = {
    "专业男声": "ad8d48dfaee44e1fa64a2e6f27448c60",
    "专业女声": "5a2403e41f5d4bc68d1bb5eb8b6cf52f",
    "商务男声": "54a5170264694bfc8e9ad98df7bd89c3",
    "温和女声": "e4642e5f-f4b1-4b80-8399-d1e71c9f8453",
}
DEFAULT_VOICE_ID = "ad8d48dfaee44e1fa64a2e6f27448c60"  # 专业男声

# Silence padding between pages (0.8 seconds)
PAGE_PAUSE_MS = 800


async def text_to_speech(
    text: str,
    voice_id: str | None = None,
    speed: float = 1.0,
    fmt: str = "mp3",
) -> bytes:
    """Convert text to speech. Returns raw MP3/WAV bytes."""
    from app.core.config import get_settings
    settings = get_settings()

    provider = settings.tts_provider.lower()
    if provider == "fish_audio" and settings.fish_audio_api_key:
        return await _fish_audio_tts(
            text=text,
            voice_id=voice_id or DEFAULT_VOICE_ID,
            speed=speed,
            fmt=fmt,
            api_key=settings.fish_audio_api_key,
            base_url=settings.fish_audio_base_url,
        )
    logger.warning("TTS_PROVIDER=%s or no API key — using stub TTS", provider)
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
