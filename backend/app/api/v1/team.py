"""Team management API — invite links + member list."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.team_invite import TeamInvite
from app.models.user import User
from app.models.tenant import Tenant
from app.services.quota_service import increment_usage

router = APIRouter(prefix="/team", tags=["team"])

INVITE_CODE_LEN = 12
DEFAULT_EXPIRE_DAYS = 7


# ── Schemas ───────────────────────────────────────────────────────────────

class CreateInviteRequest(BaseModel):
    max_uses: int = 10
    grant_role: str = "presenter"       # presenter | manager
    note: Optional[str] = None
    expire_days: int = DEFAULT_EXPIRE_DAYS


class JoinTeamRequest(BaseModel):
    invite_code: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/members")
async def list_members(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all members of the current tenant."""
    result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
        .order_by(User.created_at.asc())
    )
    members = result.scalars().all()
    return [
        {
            "id": m.id,
            "name": m.display_name,
            "email": m.email,
            "phone": m.phone,
            "role": m.role,
            "avatar_url": m.avatar_url,
            "profile_completeness": m.profile_completeness,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in members
    ]


@router.post("/invites", status_code=201)
async def create_invite(
    body: CreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create an invite link (manager/admin only)."""
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(403, "Only managers can create invites")

    if body.grant_role not in ("presenter", "manager"):
        raise HTTPException(400, "grant_role must be 'presenter' or 'manager'")

    code = secrets.token_urlsafe(INVITE_CODE_LEN)[:INVITE_CODE_LEN].upper()
    invite = TeamInvite(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        invite_code=code,
        max_uses=min(body.max_uses, 100),
        grant_role=body.grant_role,
        note=body.note,
        expires_at=datetime.utcnow() + timedelta(days=body.expire_days),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return _serialize_invite(invite)


@router.get("/invites")
async def list_invites(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List active invite links for the tenant."""
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(403, "Only managers can view invites")

    result = await db.execute(
        select(TeamInvite)
        .where(TeamInvite.tenant_id == current_user.tenant_id)
        .order_by(TeamInvite.created_at.desc())
    )
    invites = result.scalars().all()
    return [_serialize_invite(i) for i in invites]


@router.get("/invites/{code}/preview")
async def preview_invite(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint: preview invite info before joining (no auth required)."""
    invite = await _get_valid_invite(code, db)
    tenant = await db.get(Tenant, invite.tenant_id)
    return {
        "invite_code": invite.invite_code,
        "company_name": tenant.name if tenant else "未知公司",
        "grant_role": invite.grant_role,
        "note": invite.note,
        "is_valid": invite.is_valid,
    }


@router.post("/join")
async def join_team(
    body: JoinTeamRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Join a team via invite code (authenticated user, must be a new tenant member)."""
    invite = await _get_valid_invite(body.invite_code, db)

    # Check user isn't already in this tenant
    if current_user.tenant_id == invite.tenant_id:
        raise HTTPException(400, "您已是该团队成员")

    # Switch user to the invited tenant
    current_user.tenant_id = invite.tenant_id
    current_user.role = invite.grant_role

    # Increment invite usage
    invite.used_count += 1
    await db.commit()

    # Referral reward: every 3 accepted invites → give the inviter 50 bonus narration pages
    # We sum used_count across all invite codes created by this user
    total_accepted_res = await db.execute(
        select(func.sum(TeamInvite.used_count)).where(
            TeamInvite.created_by == invite.created_by,
            TeamInvite.tenant_id == invite.tenant_id,
        )
    )
    total_accepted = total_accepted_res.scalar() or 0

    bonus_granted = False
    if total_accepted > 0 and total_accepted % 3 == 0:
        # Fetch the creator to grant them the bonus
        creator = await db.get(User, invite.created_by)
        if creator:
            # Grant -50 credit (effective 50 extra narration pages this month)
            await increment_usage(
                "narration_pages",
                creator,
                db,
                delta=-50,
                meta={"reason": "referral_bonus", "total_invited": total_accepted},
            )
            await db.commit()
            bonus_granted = True

    return {
        "message": "成功加入团队",
        "tenant_id": invite.tenant_id,
        "role": invite.grant_role,
        "referral_bonus_granted": bonus_granted,
    }


@router.delete("/invites/{invite_id}", status_code=204)
async def revoke_invite(
    invite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Revoke (delete) an invite link."""
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(403, "Only managers can revoke invites")
    invite = await db.get(TeamInvite, invite_id)
    if not invite or invite.tenant_id != current_user.tenant_id:
        raise HTTPException(404)
    await db.delete(invite)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────

async def _get_valid_invite(code: str, db: AsyncSession) -> TeamInvite:
    result = await db.execute(
        select(TeamInvite).where(TeamInvite.invite_code == code.upper())
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(404, "邀请码不存在")
    if not invite.is_valid:
        raise HTTPException(400, "邀请码已过期或已达使用上限")
    return invite


def _serialize_invite(invite: TeamInvite) -> dict:
    return {
        "id": invite.id,
        "invite_code": invite.invite_code,
        "grant_role": invite.grant_role,
        "note": invite.note,
        "max_uses": invite.max_uses,
        "used_count": invite.used_count,
        "is_valid": invite.is_valid,
        "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
        "created_at": invite.created_at.isoformat(),
    }
