"""
ASR adapter — pluggable between DashScope Paraformer, Whisper, and stub.

Provider selection via ASR_PROVIDER env / config:
  - "paraformer"  →  DashScope compatible-mode API (paraformer-v2), same key as LLM
  - "whisper"     →  OpenAI Whisper API
  - "stub"        →  Placeholder text (for testing without audio infra)

Segment format returned by all providers:
  [{"text": "...", "start": 0.0, "end": 2.5}, ...]
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

TranscriptSegments = list[dict[str, Any]]


async def transcribe(audio_bytes: bytes, language: str = "zh") -> TranscriptSegments:
    """Transcribe audio bytes. Provider chosen from settings / ASR_PROVIDER env var."""
    from app.core.config import get_settings
    settings = get_settings()

    provider = settings.asr_provider.lower()

    if provider == "paraformer":
        return await _transcribe_paraformer(audio_bytes, language)
    elif provider == "whisper":
        return await _transcribe_whisper(audio_bytes, language)
    else:
        logger.warning("ASR_PROVIDER=%s — using stub transcription", provider)
        return _stub_transcribe(audio_bytes)


# ---------------------------------------------------------------------------
# DashScope Paraformer (compatible-mode OpenAI-style endpoint)
# ---------------------------------------------------------------------------

async def _transcribe_paraformer(audio_bytes: bytes, language: str) -> TranscriptSegments:
    """
    Transcribe via DashScope Paraformer V2 using the OpenAI-compatible endpoint.

    Endpoint: POST https://dashscope.aliyuncs.com/compatible-mode/v1/audio/transcriptions
    Model:    paraformer-v2  (superior Chinese ASR, also handles mixed CN/EN)
    Format:   multipart/form-data  (identical to OpenAI Whisper API)

    Returns segments with character-level timestamps.
    Falls back to full-text segment if timestamp data unavailable.
    """
    import httpx
    from app.core.config import get_settings

    settings = get_settings()

    if not settings.llm_api_key:
        logger.warning("llm_api_key not set — falling back to stub ASR")
        return _stub_transcribe(audio_bytes)

    # Detect audio format from magic bytes
    suffix = _detect_suffix(audio_bytes)

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        url = f"{settings.embedding_base_url.rsplit('/compatible-mode/v1', 1)[0]}/compatible-mode/v1/audio/transcriptions"
        # Normalise: always use the DashScope compatible-mode base
        if "dashscope" in settings.llm_base_url:
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/audio/transcriptions"
        elif settings.llm_base_url.endswith("/v1"):
            url = settings.llm_base_url.replace("/v1", "") + "/audio/transcriptions"
        else:
            url = settings.llm_base_url + "/audio/transcriptions"

        async with httpx.AsyncClient(timeout=120) as client:
            with open(tmp_path, "rb") as f:
                files = {"file": (f"audio{suffix}", f, _mime_for_suffix(suffix))}
                data = {
                    "model": "paraformer-v2",
                    "language": language,
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "segment",
                }
                headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
                resp = await client.post(url, files=files, data=data, headers=headers)
                resp.raise_for_status()
                result = resp.json()

        return _parse_verbose_json(result)

    except httpx.HTTPStatusError as e:
        logger.error(f"Paraformer API error {e.response.status_code}: {e.response.text[:300]}")
        return _stub_transcribe(audio_bytes)
    except Exception as e:
        logger.error(f"Paraformer transcription failed: {e}")
        return _stub_transcribe(audio_bytes)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _parse_verbose_json(result: dict) -> TranscriptSegments:
    """Parse OpenAI verbose_json transcription response."""
    segments: TranscriptSegments = []

    raw_segments = result.get("segments") or result.get("results") or []
    if raw_segments:
        for seg in raw_segments:
            segments.append({
                "text": (seg.get("text") or seg.get("transcript") or "").strip(),
                "start": float(seg.get("start", 0)),
                "end": float(seg.get("end", 0)),
            })
        return segments

    # Fallback: whole transcript as single segment
    full_text = result.get("text", "").strip()
    if full_text:
        # Try to estimate duration from word timestamps
        words = result.get("words", [])
        end_time = float(words[-1].get("end", 60)) if words else 60.0
        segments.append({"text": full_text, "start": 0.0, "end": end_time})

    return segments


# ---------------------------------------------------------------------------
# Whisper via OpenAI SDK
# ---------------------------------------------------------------------------

async def _transcribe_whisper(audio_bytes: bytes, language: str) -> TranscriptSegments:
    """Transcribe via OpenAI Whisper API (or compatible endpoint)."""
    import openai
    from app.core.config import get_settings

    settings = get_settings()
    client = openai.AsyncOpenAI(api_key=settings.llm_api_key)

    suffix = _detect_suffix(audio_bytes)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
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
        segments: TranscriptSegments = []
        for seg in (resp.segments or []):
            segments.append({
                "text": seg.text.strip(),
                "start": seg.start,
                "end": seg.end,
            })
        return segments
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return _stub_transcribe(audio_bytes)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Audio format detection
# ---------------------------------------------------------------------------

def _detect_suffix(audio_bytes: bytes) -> str:
    """Guess audio format from magic bytes."""
    if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
        return ".mp3"
    if audio_bytes[:4] == b"fLaC":
        return ".flac"
    if audio_bytes[:4] == b"OggS":
        return ".ogg"
    if audio_bytes[:4] == b"RIFF":
        return ".wav"
    if audio_bytes[:4] == b"ftyp" or audio_bytes[4:8] == b"ftyp":
        return ".m4a"
    # Default: webm/opus from browser MediaRecorder
    return ".webm"


def _mime_for_suffix(suffix: str) -> str:
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".webm": "audio/webm",
    }.get(suffix, "audio/webm")


# ---------------------------------------------------------------------------
# Stub
# ---------------------------------------------------------------------------

def _stub_transcribe(audio_bytes: bytes) -> TranscriptSegments:
    """Fake transcription for testing without a real ASR service."""
    size_kb = len(audio_bytes) / 1024
    estimated_dur = max(10.0, size_kb / 500 * 60)
    return [
        {
            "text": "（ASR 服务未配置，此为占位转录文本。请在 .env 中设置 ASR_PROVIDER=paraformer 及 LLM_API_KEY）",
            "start": 0.0,
            "end": estimated_dur,
        }
    ]
