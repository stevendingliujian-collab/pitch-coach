"""
Open API 管理 — API Key + Webhook 订阅 + 用量统计

功能：
- API Key CRUD（创建、列表、撤销）
- Webhook 订阅管理（创建、列表、删除、测试）
- API 用量统计（按 Key、按端点）
- Open API 文档快速入口（重定向到 /docs）

API Key 格式：pc_live_<32字节随机十六进制>
- 首12字符（pc_live_xxxx）存储为 key_prefix（展示用）
- 完整 key 的 SHA-256 存储为 key_hash（验证用）
- 完整 key 只在创建时返回一次，之后不可再查

认证中间件：PitchCoachAPIKeyMiddleware（在 routers 之前注册）
- 解析请求头 Authorization: Bearer pc_live_...
- 查找 key_hash，验证 is_active 和 expires_at
- 将 tenant_id 注入请求 state（供后续路由使用）
- 记录 api_usage
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import PcUser
from app.models.post_mortem import ApiKey, ApiUsage

router = APIRouter(prefix="/open-api", tags=["open-api"])

# ─── Constants ────────────────────────────────────────────────────────────────

API_KEY_PREFIX = "pc_live_"
API_KEY_LENGTH = 32  # bytes → 64 hex chars

SCOPES = ["read", "write", "webhook", "admin"]

AVAILABLE_EVENTS = [
    "rehearsal.completed",
    "rehearsal.scored",
    "plan.generated",
    "post_mortem.completed",
    "subscription.upgraded",
    "subscription.expired",
    "team.member_joined",
]


# ─── Helper: generate key ─────────────────────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """Returns (full_key, key_hash, key_prefix)"""
    raw = secrets.token_hex(API_KEY_LENGTH)
    full_key = API_KEY_PREFIX + raw
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:12]
    return full_key, key_hash, key_prefix


def hash_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode()).hexdigest()


# ─── API Key management ───────────────────────────────────────────────────────

@router.post("/keys", status_code=201)
async def create_api_key(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    创建新的 API Key。完整 key 只返回一次，之后不可再查。

    body: {
        "name": "我的应用",
        "scopes": ["read", "write"],
        "expires_days": 365  // null = 永不过期
    }
    """
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    scopes = body.get("scopes", ["read"])
    invalid = [s for s in scopes if s not in SCOPES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid scopes: {invalid}")

    expires_days = body.get("expires_days")
    expires_at = datetime.utcnow() + timedelta(days=int(expires_days)) if expires_days else None

    full_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,  # ⚠️ Shown ONLY once
        "key_prefix": key_prefix,
        "scopes": api_key.scopes,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "created_at": api_key.created_at.isoformat(),
        "warning": "请立即保存此 API Key，关闭后将无法再次查看完整密钥"
    }


@router.get("/keys")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """列出所有 API Key（不含完整 key）"""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.tenant_id == current_user.tenant_id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    # Get usage counts
    usage_result = await db.execute(
        select(ApiUsage.api_key_id, func.count(ApiUsage.id).label("count"))
        .where(ApiUsage.tenant_id == current_user.tenant_id)
        .group_by(ApiUsage.api_key_id)
    )
    usage_map = {row.api_key_id: row.count for row in usage_result}

    return [_key_summary(k, usage_map.get(k.id, 0)) for k in keys]


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """撤销 API Key（软删除：设置 is_active=False）"""
    key = await db.get(ApiKey, key_id)
    if not key or key.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.commit()


@router.patch("/keys/{key_id}")
async def update_api_key(
    key_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """更新 API Key 名称或 scopes"""
    key = await db.get(ApiKey, key_id)
    if not key or key.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="API key not found")
    if "name" in body:
        key.name = body["name"]
    if "scopes" in body:
        invalid = [s for s in body["scopes"] if s not in SCOPES]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid scopes: {invalid}")
        key.scopes = body["scopes"]
    await db.commit()
    await db.refresh(key)
    return _key_summary(key, 0)


# ─── API Usage stats ──────────────────────────────────────────────────────────

@router.get("/usage")
async def get_api_usage(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取 API 用量统计（最近 N 天）"""
    since = datetime.utcnow() - timedelta(days=days)

    # Total calls
    total_result = await db.execute(
        select(func.count(ApiUsage.id))
        .where(
            ApiUsage.tenant_id == current_user.tenant_id,
            ApiUsage.created_at >= since,
        )
    )
    total_calls = total_result.scalar() or 0

    # By endpoint
    endpoint_result = await db.execute(
        select(ApiUsage.endpoint, func.count(ApiUsage.id).label("count"))
        .where(
            ApiUsage.tenant_id == current_user.tenant_id,
            ApiUsage.created_at >= since,
        )
        .group_by(ApiUsage.endpoint)
        .order_by(func.count(ApiUsage.id).desc())
        .limit(10)
    )
    by_endpoint = [
        {"endpoint": row.endpoint, "count": row.count}
        for row in endpoint_result
    ]

    # By key
    key_result = await db.execute(
        select(ApiUsage.api_key_id, func.count(ApiUsage.id).label("count"))
        .where(
            ApiUsage.tenant_id == current_user.tenant_id,
            ApiUsage.created_at >= since,
        )
        .group_by(ApiUsage.api_key_id)
    )
    by_key = [
        {"api_key_id": row.api_key_id, "count": row.count}
        for row in key_result
    ]

    # Error rate
    error_result = await db.execute(
        select(func.count(ApiUsage.id))
        .where(
            ApiUsage.tenant_id == current_user.tenant_id,
            ApiUsage.created_at >= since,
            ApiUsage.status_code >= 400,
        )
    )
    error_count = error_result.scalar() or 0

    return {
        "period_days": days,
        "total_calls": total_calls,
        "error_count": error_count,
        "error_rate": round(error_count / total_calls * 100, 1) if total_calls > 0 else 0,
        "by_endpoint": by_endpoint,
        "by_key": by_key,
    }


# ─── Webhook management ───────────────────────────────────────────────────────
# Webhooks are stored as a special ApiKey with scopes=["webhook"] and
# metadata in key_prefix field (reusing the schema for simplicity).
# A dedicated webhook table would be added in a future migration.
# For now we store webhook URLs in ApiKey.key_prefix as JSON.

@router.get("/webhooks")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """获取所有 Webhook 订阅"""
    result = await db.execute(
        select(ApiKey)
        .where(
            ApiKey.tenant_id == current_user.tenant_id,
            ApiKey.name.like("webhook:%"),
            ApiKey.is_active == True,
        )
        .order_by(ApiKey.created_at.desc())
    )
    webhooks = result.scalars().all()
    return [_webhook_summary(w) for w in webhooks]


@router.post("/webhooks", status_code=201)
async def create_webhook(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """
    创建 Webhook 订阅。

    body: {
        "url": "https://your-server.com/webhook",
        "events": ["rehearsal.completed", "plan.generated"],
        "secret": "optional_signing_secret"
    }
    """
    url = (body.get("url") or "").strip()
    if not url.startswith("https://") and not url.startswith("http://"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    events = body.get("events", AVAILABLE_EVENTS)
    invalid_events = [e for e in events if e not in AVAILABLE_EVENTS]
    if invalid_events:
        raise HTTPException(status_code=400, detail=f"Unknown events: {invalid_events}")

    signing_secret = body.get("secret") or secrets.token_hex(16)

    # Store webhook as a special API key record
    webhook = ApiKey(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        name=f"webhook:{url}",
        key_hash=hashlib.sha256(signing_secret.encode()).hexdigest(),
        key_prefix=json.dumps({"url": url, "events": events}),  # hack for now
        scopes=["webhook"],
        is_active=True,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    return {
        "id": webhook.id,
        "url": url,
        "events": events,
        "signing_secret": signing_secret,  # shown only once
        "is_active": True,
        "created_at": webhook.created_at.isoformat(),
        "warning": "请保存 Signing Secret，用于验证 Webhook 签名"
    }


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    webhook = await db.get(ApiKey, webhook_id)
    if not webhook or webhook.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if not webhook.name.startswith("webhook:"):
        raise HTTPException(status_code=400, detail="Not a webhook")
    webhook.is_active = False
    await db.commit()


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: PcUser = Depends(get_current_user),
):
    """发送测试 Webhook 事件"""
    webhook = await db.get(ApiKey, webhook_id)
    if not webhook or webhook.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    try:
        meta = json.loads(webhook.key_prefix or "{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid webhook metadata")

    url = meta.get("url", "")
    payload = json.dumps({
        "event": "test",
        "tenant_id": current_user.tenant_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data": {"message": "This is a test webhook from PitchCoach AI"},
    }).encode()

    signature = hmac.new(
        webhook.key_hash.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-PitchCoach-Signature": f"sha256={signature}",
                "X-PitchCoach-Event": "test",
                "User-Agent": "PitchCoach-Webhook/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
    except urllib.error.HTTPError as e:
        status_code = e.code
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}

    return {
        "success": 200 <= status_code < 300,
        "status_code": status_code,
        "url": url,
        "message": "Webhook 测试成功" if 200 <= status_code < 300 else f"Webhook 返回 {status_code}"
    }


@router.get("/available-events")
async def list_available_events(current_user: PcUser = Depends(get_current_user)):
    """获取所有可订阅的 Webhook 事件"""
    return [
        {"event": e, "description": _event_description(e)}
        for e in AVAILABLE_EVENTS
    ]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _key_summary(key: ApiKey, usage_count: int = 0) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "scopes": key.scopes,
        "is_active": key.is_active,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "created_at": key.created_at.isoformat(),
        "usage_count": usage_count,
    }


def _webhook_summary(w: ApiKey) -> dict:
    try:
        meta = json.loads(w.key_prefix or "{}")
    except json.JSONDecodeError:
        meta = {}
    return {
        "id": w.id,
        "url": meta.get("url", ""),
        "events": meta.get("events", []),
        "is_active": w.is_active,
        "created_at": w.created_at.isoformat(),
    }


def _event_description(event: str) -> str:
    return {
        "rehearsal.completed": "排练上传完成（录音处理完毕）",
        "rehearsal.scored": "排练评分完成（AI 评分结果就绪）",
        "plan.generated": "讲解方案生成完成",
        "post_mortem.completed": "复盘分析完成",
        "subscription.upgraded": "订阅套餐升级",
        "subscription.expired": "订阅试用/套餐到期",
        "team.member_joined": "团队成员加入",
    }.get(event, event)
