"""ASR adapter — pluggable between Paraformer and Whisper (or stub)."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

# Segment format returned by any provider:
# [{"text": "...", "start": 0.0, "end": 2.5}, ...]
TranscriptSegments = list[dict[str, Any]]


async def transcribe(audio_bytes: bytes, language: str = "zh") -> TranscriptSegments:
    """Transcribe audio bytes. Provider chosen from ASR_PROVIDER env var."""
    provider = os.getenv("ASR_PROVIDER", "stub").lower()
    if provider == "whisper":
        return await _transcribe_whisper(audio_bytes, language)
    elif provider == "paraformer":
        return await _transcribe_paraformer(audio_bytes, language)
    else:
        logger.warning("ASR_PROVIDER=%s — using stub transcription", provider)
        return _stub_transcribe(audio_bytes)


# ---------------------------------------------------------------------------
# Whisper (via openai package)
# ---------------------------------------------------------------------------

async def _transcribe_whisper(audio_bytes: bytes, language: str) -> TranscriptSegments:
    import openai  # type: ignore
    from app.core.config import settings

    client = openai.AsyncOpenAI(
        api_key=settings.openai_api_key or settings.deepseek_api_key,
        base_url=settings.whisper_api_base or None,
    )
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            resp = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        segments = []
        for seg in resp.segments or []:
            segments.append({
                "text": seg.text.strip(),
                "start": seg.start,
                "end": seg.end,
            })
        return segments
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Paraformer via FunASR HTTP service
# ---------------------------------------------------------------------------

async def _transcribe_paraformer(audio_bytes: bytes, language: str) -> TranscriptSegments:
    import aiohttp  # type: ignore

    funasr_url = os.getenv("FUNASR_URL", "http://localhost:10095/api/asr")
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        async with aiohttp.ClientSession() as session:
            with open(tmp_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("audio", f, filename="audio.webm", content_type="audio/webm")
                data.add_field("language", language)
                async with session.post(funasr_url, data=data, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    result = await resp.json()

        raw_segs = result.get("segments", result.get("results", []))
        segments = []
        for seg in raw_segs:
            segments.append({
                "text": seg.get("text", "").strip(),
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
            })
        return segments
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Stub — returns placeholder so the rest of the pipeline keeps working
# ---------------------------------------------------------------------------

def _stub_transcribe(audio_bytes: bytes) -> TranscriptSegments:
    """Fake transcription for testing without a real ASR service."""
    size_kb = len(audio_bytes) / 1024
    # Estimate ~1 minute per 500KB webm/opus
    estimated_dur = max(10.0, size_kb / 500 * 60)
    return [
        {
            "text": "（ASR_PROVIDER=stub，此为占位转录文本，请配置真实 ASR 服务）",
            "start": 0.0,
            "end": estimated_dur,
        }
    ]
