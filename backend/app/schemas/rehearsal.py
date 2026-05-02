from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PageTiming(BaseModel):
    page_number: int
    start_sec: float
    end_sec: float


class StartRehearsalRequest(BaseModel):
    pitch_task_id: int
    plan_id: int | None = None


class StartRehearsalResponse(BaseModel):
    rehearsal_id: int
    upload_url: str     # presigned MinIO PUT URL
    object_key: str


class CompleteRehearsalRequest(BaseModel):
    object_key: str             # MinIO key of uploaded audio
    audio_duration: int         # seconds
    page_timings: list[PageTiming] = Field(default_factory=list)


class RehearsalStatusResponse(BaseModel):
    rehearsal_id: int
    status: int
    total_score: float | None = None
    fluency_score: float | None = None
    rate_score: float | None = None
    timing_score: float | None = None


class FillerWordDetail(BaseModel):
    word: str
    count: int
    positions: list[int]


class PageScore(BaseModel):
    page_number: int
    actual_duration_sec: float
    suggested_duration_sec: float
    timing_ok: bool
    importance_level: int


class RehearsalReportResponse(BaseModel):
    rehearsal_id: int
    pitch_task_id: int
    status: int
    audio_url: str
    audio_duration: int
    total_score: float | None = None
    fluency_score: float | None = None
    rate_score: float | None = None
    timing_score: float | None = None
    filler_count: int | None = None
    filler_detail: list[FillerWordDetail] = Field(default_factory=list)
    chars_per_min: float | None = None
    total_duration_sec: float | None = None
    improvement_tips: list[str] = Field(default_factory=list)
    page_scores: list[PageScore] = Field(default_factory=list)
    page_timings: list[PageTiming] = Field(default_factory=list)
    created_at: datetime


class RehearsalListItem(BaseModel):
    rehearsal_id: int
    pitch_task_id: int
    status: int
    total_score: float | None = None
    audio_duration: int
    created_at: datetime
