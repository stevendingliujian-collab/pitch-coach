"""F5 经理审核与就绪认证 API."""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_presigned_download_url
from app.models.rehearsal import Rehearsal
from app.models.review import ReviewComment, Certification
from app.models.pitch_task import PitchTask

router = APIRouter(tags=["reviews"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AddCommentRequest(BaseModel):
    timestamp_sec: float
    comment_text: str
    is_highlight: bool = False
    mentioned_user_ids: list[int] = []


class CertifyRequest(BaseModel):
    rehearsal_id: int
    pitch_task_id: int
    user_id: int
    decision: str      # "approve" | "reject"
    comment: str = ""


class SubmitForReviewRequest(BaseModel):
    rehearsal_id: int


# ---------------------------------------------------------------------------
# Review Comments
# ---------------------------------------------------------------------------

@router.post("/rehearsals/{rehearsal_id}/comments", status_code=201)
async def add_comment(
    rehearsal_id: int,
    body: AddCommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manager adds a timestamped comment on a rehearsal recording."""
    rehearsal = await db.get(Rehearsal, rehearsal_id)
    if not rehearsal or rehearsal.tenant_id != current_user.tenant_id:
        raise HTTPException(404)

    comment = ReviewComment(
        rehearsal_id=rehearsal_id,
        reviewer_id=current_user.id,
        timestamp_sec=body.timestamp_sec,
        comment_text=body.comment_text,
        is_highlight=body.is_highlight,
        mentioned_users=body.mentioned_user_ids or None,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {
        "id": comment.id,
        "timestamp_sec": float(comment.timestamp_sec),
        "comment_text": comment.comment_text,
        "is_highlight": comment.is_highlight,
        "reviewer_id": comment.reviewer_id,
        "created_at": comment.created_at.isoformat(),
    }


@router.get("/rehearsals/{rehearsal_id}/comments")
async def list_comments(
    rehearsal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all comments on a rehearsal, ordered by timestamp."""
    rehearsal = await db.get(Rehearsal, rehearsal_id)
    if not rehearsal or rehearsal.tenant_id != current_user.tenant_id:
        raise HTTPException(404)

    result = await db.execute(
        select(ReviewComment)
        .where(ReviewComment.rehearsal_id == rehearsal_id)
        .order_by(ReviewComment.timestamp_sec)
    )
    comments = result.scalars().all()
    return [
        {
            "id": c.id,
            "timestamp_sec": float(c.timestamp_sec),
            "comment_text": c.comment_text,
            "is_highlight": c.is_highlight,
            "reviewer_id": c.reviewer_id,
            "mentioned_users": c.mentioned_users,
            "created_at": c.created_at.isoformat(),
        }
        for c in comments
    ]


@router.delete("/rehearsals/{rehearsal_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    rehearsal_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    comment = await db.get(ReviewComment, comment_id)
    if not comment or comment.rehearsal_id != rehearsal_id:
        raise HTTPException(404)
    if comment.reviewer_id != current_user.id:
        raise HTTPException(403, "Only the reviewer can delete their own comments")
    await db.delete(comment)
    await db.commit()


# ---------------------------------------------------------------------------
# Submit for review (by presenter)
# ---------------------------------------------------------------------------

@router.post("/rehearsals/{rehearsal_id}/submit-review", status_code=200)
async def submit_for_review(
    rehearsal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Presenter submits a completed rehearsal to their manager for review."""
    rehearsal = await db.get(Rehearsal, rehearsal_id)
    if not rehearsal or rehearsal.tenant_id != current_user.tenant_id:
        raise HTTPException(404)
    if rehearsal.user_id != current_user.id:
        raise HTTPException(403, "Only the rehearsal owner can submit for review")
    if rehearsal.status not in (3,):  # must be scored
        raise HTTPException(400, "Rehearsal must be scored before submitting for review")

    rehearsal.status = 4  # submitted for review
    rehearsal.submitted_at = datetime.utcnow()
    await db.commit()
    return {"status": "submitted"}


# ---------------------------------------------------------------------------
# Manager review queue
# ---------------------------------------------------------------------------

@router.get("/reviews/pending")
async def list_pending_reviews(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manager view: all rehearsals awaiting review, sorted by bid date urgency."""
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(403, "Only managers can view review queue")

    result = await db.execute(
        select(Rehearsal, PitchTask)
        .join(PitchTask, Rehearsal.pitch_task_id == PitchTask.id)
        .where(
            Rehearsal.tenant_id == current_user.tenant_id,
            Rehearsal.status == 4,
        )
        .order_by(PitchTask.bid_date.asc().nullslast())
    )
    rows = result.all()
    items = []
    for rehearsal, task in rows:
        audio_url = None
        if rehearsal.audio_url:
            try:
                audio_url = get_presigned_download_url(rehearsal.audio_url)
            except Exception:
                audio_url = rehearsal.audio_url

        # Urgency flag: ≤48h to bid date
        urgent = False
        if task.bid_date:
            from datetime import timezone
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            diff = (task.bid_date - now).total_seconds()
            urgent = 0 < diff <= 48 * 3600

        items.append({
            "rehearsal_id": rehearsal.id,
            "pitch_task_id": task.id,
            "task_name": task.name,
            "user_id": rehearsal.user_id,
            "total_score": float(rehearsal.total_score) if rehearsal.total_score else None,
            "audio_duration": rehearsal.audio_duration,
            "audio_url": audio_url,
            "bid_date": task.bid_date.isoformat() if task.bid_date else None,
            "urgent": urgent,
            "submitted_at": rehearsal.submitted_at.isoformat() if rehearsal.submitted_at else None,
        })
    return items


# ---------------------------------------------------------------------------
# Certification (manager decision)
# ---------------------------------------------------------------------------

@router.post("/certifications", status_code=201)
async def certify_rehearsal(
    body: CertifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Manager approves or rejects a rehearsal, issuing/declining certification."""
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(403, "Only managers can certify")

    rehearsal = await db.get(Rehearsal, body.rehearsal_id)
    if not rehearsal or rehearsal.tenant_id != current_user.tenant_id:
        raise HTTPException(404, "Rehearsal not found")

    decision_status = {"approve": 1, "reject": 2}.get(body.decision)
    if decision_status is None:
        raise HTTPException(400, "decision must be 'approve' or 'reject'")

    # Upsert certification for this task+user
    existing = await db.execute(
        select(Certification).where(
            Certification.tenant_id == current_user.tenant_id,
            Certification.pitch_task_id == body.pitch_task_id,
            Certification.user_id == body.user_id,
        )
    )
    cert = existing.scalar_one_or_none()
    if cert:
        cert.status = decision_status
        cert.review_comment = body.comment
        cert.reviewer_id = current_user.id
        cert.rehearsal_id = body.rehearsal_id
        cert.certified_at = datetime.utcnow()
    else:
        cert = Certification(
            tenant_id=current_user.tenant_id,
            pitch_task_id=body.pitch_task_id,
            user_id=body.user_id,
            reviewer_id=current_user.id,
            rehearsal_id=body.rehearsal_id,
            status=decision_status,
            review_comment=body.comment,
            certified_at=datetime.utcnow(),
        )
        db.add(cert)

    # Update rehearsal status accordingly
    rehearsal.status = 5 if decision_status == 1 else 6

    await db.commit()
    await db.refresh(cert)

    # TODO: send notification (WeChat/Feishu webhook) — P1 later
    return {
        "cert_id": cert.id,
        "status": "approved" if decision_status == 1 else "rejected",
        "rehearsal_status": rehearsal.status,
    }


@router.get("/certifications/{pitch_task_id}")
async def get_certification(
    pitch_task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the latest certification for a pitch task (current user)."""
    result = await db.execute(
        select(Certification).where(
            Certification.tenant_id == current_user.tenant_id,
            Certification.pitch_task_id == pitch_task_id,
            Certification.user_id == current_user.id,
        )
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(404)
    return {
        "cert_id": cert.id,
        "status": cert.status,
        "status_label": {0: "待审核", 1: "已通过", 2: "需改进"}.get(cert.status, ""),
        "review_comment": cert.review_comment,
        "certified_at": cert.certified_at.isoformat() if cert.certified_at else None,
    }
