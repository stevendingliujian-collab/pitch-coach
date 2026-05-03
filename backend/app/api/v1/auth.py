"""
Authentication API — 登录注册合一

支持的认证方式：
  1. 手机号 + 验证码（P0 主要方式）
  2. 微信扫码（P0，PC Web）
  3. 邮箱 + 密码（P1，作为备选）
  4. 企业微信 OAuth2（P1）
  5. 飞书 OAuth2（P1）
  6. CRM SSO Token（P1）

身份合并规则：unionid → phone → email → 创建新用户
"""
from __future__ import annotations

import hashlib
import logging
import random
import secrets
import string
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    EmailLoginRequest,
    EmailRegisterRequest,
    PhoneLoginRequest,
    PhoneSendCodeRequest,
    ProfileUpdateRequest,
    TokenResponse,
    UserProfile,
    WechatCallbackRequest,
    WechatQrcodeResponse,
    WechatQrcodeStatusResponse,
)
from app.services.conversion_service import track_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ── Redis helpers ─────────────────────────────────────────────────────────────

def _get_redis():
    import redis.asyncio as aioredis
    settings = get_settings()
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def _redis_set(key: str, value: str, ttl: int) -> None:
    r = _get_redis()
    await r.setex(key, ttl, value)
    await r.aclose()


async def _redis_get(key: str) -> str | None:
    r = _get_redis()
    val = await r.get(key)
    await r.aclose()
    return val


async def _redis_delete(key: str) -> None:
    r = _get_redis()
    await r.delete(key)
    await r.aclose()


async def _redis_incr_expire(key: str, ttl: int) -> int:
    r = _get_redis()
    pipe = r.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, ttl)
    results = await pipe.execute()
    await r.aclose()
    return results[0]


# ── Identity merge helpers ────────────────────────────────────────────────────

async def _find_or_create_user(
    db: AsyncSession,
    *,
    wechat_unionid: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    crm_user_id: str | None = None,
    # Defaults for new user creation
    name: str | None = None,
    avatar_url: str | None = None,
    register_source: str = "web",
    register_channel: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> tuple[User, bool]:
    """
    按优先级查找已有用户，不存在则创建。
    返回 (user, is_new_user)
    """
    user: User | None = None

    # 1. unionid
    if wechat_unionid:
        result = await db.execute(
            select(User).where(User.wechat_unionid == wechat_unionid, User.status == 1)
        )
        user = result.scalar_one_or_none()

    # 2. CRM user id
    if user is None and crm_user_id:
        result = await db.execute(
            select(User).where(User.crm_user_id == crm_user_id, User.status == 1)
        )
        user = result.scalar_one_or_none()

    # 3. phone
    if user is None and phone:
        result = await db.execute(
            select(User).where(User.phone == phone, User.status == 1)
        )
        user = result.scalar_one_or_none()

    # 4. email
    if user is None and email:
        result = await db.execute(
            select(User).where(User.email == email, User.status == 1)
        )
        user = result.scalar_one_or_none()

    if user is not None:
        # Bind new identity to existing user
        changed = False
        if wechat_unionid and not user.wechat_unionid:
            user.wechat_unionid = wechat_unionid
            changed = True
        if phone and not user.phone:
            user.phone = phone
            changed = True
        if email and not user.email:
            user.email = email
            changed = True
        if crm_user_id and not user.crm_user_id:
            user.crm_user_id = crm_user_id
            changed = True
        if extra_fields:
            for k, v in extra_fields.items():
                if v and not getattr(user, k, None):
                    setattr(user, k, v)
                    changed = True
        if changed:
            user.recalculate_completeness()
            await db.commit()
            await db.refresh(user)
        return user, False

    # Create new user + personal tenant
    tenant = Tenant(name=f"个人-placeholder", plan_type="free", max_users=1)
    db.add(tenant)
    await db.flush()  # get tenant.id

    tenant.name = f"个人-{tenant.id}"

    user = User(
        tenant_id=tenant.id,
        phone=phone,
        email=email,
        name=name,
        avatar_url=avatar_url,
        wechat_unionid=wechat_unionid,
        crm_user_id=crm_user_id,
        register_source=register_source,
        register_channel=register_channel,
        role="owner",
        status=1,
    )
    if extra_fields:
        for k, v in extra_fields.items():
            setattr(user, k, v)

    db.add(user)
    await db.flush()
    user.recalculate_completeness()
    await db.commit()
    await db.refresh(user)
    return user, True


def _make_token(user: User, plan: str = "free") -> str:
    return create_access_token({
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "role": user.role,
        "plan": plan,
        "source": user.last_login_source or user.register_source,
    })


async def _get_effective_plan(user: User, db: AsyncSession) -> str:
    """Look up the tenant's active subscription and return 'pro', 'elite', or 'free'."""
    try:
        result = await db.execute(
            select(Subscription).where(Subscription.tenant_id == user.tenant_id)
        )
        sub = result.scalar_one_or_none()
        if sub and sub.is_active:
            return sub.plan_type or "pro"
    except Exception:
        pass
    return "free"


async def _token_response(user: User, db: AsyncSession, is_new_user: bool = False) -> TokenResponse:
    plan = await _get_effective_plan(user, db)
    return TokenResponse(
        access_token=_make_token(user, plan),
        user_id=user.id,
        name=user.display_name,
        tenant_id=user.tenant_id,
        role=user.role,
        is_new_user=is_new_user,
        profile_completeness=user.profile_completeness,
    )


# ═════════════════════════════════════════════════════════════════════════════
# 1. 手机号 + 验证码
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/sms/send", status_code=200)
async def sms_send(body: PhoneSendCodeRequest, request: Request):
    """
    发送手机验证码。
    限流：同手机号 60s 内不可重发；同 IP 10 分钟内 ≤5 条。
    开发模式（sms_provider=stub）：不发短信，code 写入 Redis 并日志输出。
    """
    settings = get_settings()
    phone = body.phone

    # --- 限流：手机号 60s 冷却 ---
    cd_key = f"sms:cd:{phone}"
    if await _redis_get(cd_key):
        raise HTTPException(status_code=429, detail="请稍后再试（60秒内只能发送一次）")

    # --- 限流：IP 10min ≤5 条 ---
    client_ip = request.client.host if request.client else "unknown"
    ip_key = f"sms:ip:{client_ip}"
    count = await _redis_incr_expire(ip_key, 600)
    if count > settings.sms_ip_rate_limit:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    # --- 生成 6 位验证码 ---
    code = "".join(random.choices(string.digits, k=6))
    code_key = f"sms:code:{phone}"
    await _redis_set(code_key, code, settings.sms_code_ttl)
    await _redis_set(cd_key, "1", settings.sms_resend_interval)

    # --- 发送 ---
    if settings.sms_provider == "stub":
        logger.warning("📱 [SMS-STUB] phone=%s  code=%s  (开发模式，不发真实短信)", phone, code)
    else:
        await _send_real_sms(phone, code, settings)

    return {"message": "验证码已发送", "ttl": settings.sms_code_ttl}


async def _send_real_sms(phone: str, code: str, settings) -> None:
    """阿里云 / 腾讯云 SMS — P1 生产接入时实现"""
    raise NotImplementedError("Real SMS provider not configured")


@router.post("/sms/login", response_model=TokenResponse)
async def sms_login(body: PhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    """手机号 + 验证码登录 / 注册合一。"""
    code_key = f"sms:code:{body.phone}"
    stored = await _redis_get(code_key)

    if not stored or stored != body.code:
        raise HTTPException(status_code=401, detail="验证码错误或已过期")

    await _redis_delete(code_key)

    user, is_new = await _find_or_create_user(
        db,
        phone=body.phone,
        register_source="phone",
        register_channel=body.channel,
    )
    user.last_login_at = datetime.utcnow()
    user.last_login_source = "phone"
    await db.commit()

    if is_new:
        await track_event("user_registered", user, db,
                          properties={"method": "phone"})
    else:
        await track_event("user_logged_in", user, db,
                          properties={"method": "phone", "is_returning": True})

    return await _token_response(user, db, is_new_user=is_new)


# ═════════════════════════════════════════════════════════════════════════════
# 2. 微信扫码（PC Web）
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/wechat/qrcode", response_model=WechatQrcodeResponse)
async def wechat_qrcode():
    """
    生成微信扫码登录二维码。
    开发 stub：返回占位图，session_key 存 Redis 300s。
    生产：调用微信开放平台 /connect/qrconnect 换取 qrcode_url。
    """
    settings = get_settings()
    session_key = secrets.token_urlsafe(24)
    state_key = f"wx:qr:{session_key}"
    await _redis_set(state_key, "pending", settings.wechat_qrcode_ttl)

    if settings.wechat_app_id:
        # 生产：构造微信扫码跳转 URL
        qrcode_url = (
            f"https://open.weixin.qq.com/connect/qrconnect"
            f"?appid={settings.wechat_app_id}"
            f"&redirect_uri={settings.wechat_redirect_uri}"
            f"&response_type=code&scope=snsapi_login"
            f"&state={session_key}"
        )
    else:
        # 开发 stub：返回占位二维码图片
        qrcode_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=wechat_login_{session_key}"

    return WechatQrcodeResponse(
        qrcode_url=qrcode_url,
        session_key=session_key,
        expires_in=settings.wechat_qrcode_ttl,
    )


@router.get("/wechat/qrcode/status", response_model=WechatQrcodeStatusResponse)
async def wechat_qrcode_status(session_key: str, db: AsyncSession = Depends(get_db)):
    """
    前端每 2s 轮询扫码状态。
    状态值：pending → scanned → confirmed（含 token）→ expired
    """
    state_key = f"wx:qr:{session_key}"
    state = await _redis_get(state_key)

    if state is None:
        return WechatQrcodeStatusResponse(status="expired")

    if state == "pending":
        return WechatQrcodeStatusResponse(status="pending")

    if state == "scanned":
        return WechatQrcodeStatusResponse(status="scanned")

    if state.startswith("confirmed:"):
        user_id = int(state.split(":", 1)[1])
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        await _redis_delete(state_key)
        if user:
            return WechatQrcodeStatusResponse(
                status="confirmed",
                token_response=await _token_response(user, db),
            )

    return WechatQrcodeStatusResponse(status="expired")


@router.post("/wechat/callback", response_model=TokenResponse)
async def wechat_callback(body: WechatCallbackRequest, db: AsyncSession = Depends(get_db)):
    """
    微信 OAuth2 回调：code → access_token → openid/unionid → 查找/创建用户。
    state 即 session_key，用于通知轮询端。
    """
    settings = get_settings()

    # --- 开发 stub：直接用 code 作为 unionid 测试 ---
    if not settings.wechat_app_id:
        unionid = f"stub_unionid_{body.code}"
        openid = f"stub_openid_{body.code}"
        wx_name = "微信用户"
        wx_avatar = ""
    else:
        # 生产：code 换 access_token
        wx_data = await _wechat_code_to_user_info(body.code, settings)
        unionid = wx_data["unionid"]
        openid = wx_data["openid"]
        wx_name = wx_data.get("nickname", "")
        wx_avatar = wx_data.get("headimgurl", "")

    user, is_new = await _find_or_create_user(
        db,
        wechat_unionid=unionid,
        name=wx_name or None,
        avatar_url=wx_avatar or None,
        register_source="wechat",
        extra_fields={"wechat_openid_web": openid},
    )
    user.last_login_at = datetime.utcnow()
    user.last_login_source = "wechat"
    await db.commit()

    # 通知轮询端
    if body.state:
        state_key = f"wx:qr:{body.state}"
        await _redis_set(state_key, f"confirmed:{user.id}", 60)

    if is_new:
        await track_event("user_registered", user, db, properties={"method": "wechat"})

    return await _token_response(user, db, is_new_user=is_new)


async def _wechat_code_to_user_info(code: str, settings) -> dict:
    """调用微信开放平台 API，code → unionid + 用户信息。"""
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1: code → access_token
        token_resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        if "errcode" in token_data:
            raise HTTPException(status_code=400, detail=f"微信授权失败: {token_data}")
        access_token = token_data["access_token"]
        openid = token_data["openid"]

        # Step 2: access_token → user info
        info_resp = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={"access_token": access_token, "openid": openid, "lang": "zh_CN"},
        )
        return info_resp.json()


# ═════════════════════════════════════════════════════════════════════════════
# 3. 邮箱 + 密码（保留，作为备选登录方式）
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: EmailRegisterRequest, db: AsyncSession = Depends(get_db)):
    """邮箱注册（备选方式，公司名改为可选）。"""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    company_name = body.company_name or None
    tenant = Tenant(
        name=company_name or "个人-placeholder",
        plan_type="free",
        max_users=1,
    )
    db.add(tenant)
    await db.flush()
    if not company_name:
        tenant.name = f"个人-{tenant.id}"

    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name or None,
        role="owner",
        register_source="web",
    )
    db.add(user)
    await db.flush()
    user.recalculate_completeness()
    await db.commit()
    await db.refresh(user)

    await track_event("user_registered", user, db,
                      properties={"method": "email", "company_name": company_name})

    return await _token_response(user, db, is_new_user=True)


@router.post("/login", response_model=TokenResponse)
async def login(body: EmailLoginRequest, db: AsyncSession = Depends(get_db)):
    """邮箱 + 密码登录。"""
    result = await db.execute(select(User).where(User.email == body.email, User.status == 1))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    user.last_login_at = datetime.utcnow()
    user.last_login_source = "email"
    await db.commit()

    return await _token_response(user, db)


# ═════════════════════════════════════════════════════════════════════════════
# 4. CRM SSO（P1）
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/sso/crm", response_model=TokenResponse)
async def crm_sso(sso_token: str, db: AsyncSession = Depends(get_db)):
    """
    OTD CRM SSO：验证 HMAC-SHA256 token，自动创建/绑定影子账号。
    token payload: crm_user_id|tenant_id|name|phone|company_name|ts
    """
    import hmac
    settings = get_settings()
    shared_secret = settings.secret_key.encode()

    try:
        parts = sso_token.split("|")
        if len(parts) < 6:
            raise ValueError("invalid format")
        crm_user_id, tenant_id_str, name, phone, company_name, ts_str = parts[:6]
        sig = parts[6] if len(parts) > 6 else ""
        ts = int(ts_str)
        if abs(time.time() - ts) > 300:
            raise ValueError("token expired")
        payload_bytes = "|".join([crm_user_id, tenant_id_str, name, phone, company_name, ts_str]).encode()
        expected = hmac.new(shared_secret, payload_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise ValueError("signature mismatch")
    except Exception as exc:
        logger.warning("CRM SSO token invalid: %s", exc)
        raise HTTPException(status_code=401, detail="SSO token 无效或已过期")

    user, is_new = await _find_or_create_user(
        db,
        crm_user_id=crm_user_id,
        phone=phone or None,
        name=name or None,
        register_source="crm_sso",
        extra_fields={"sso_provider": "otd_crm"},
    )

    # 如果提供了公司名且租户还是默认名，则更新
    if company_name:
        result = await db.execute(
            select(Tenant).where(Tenant.id == user.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant and tenant.name.startswith("个人-"):
            tenant.name = company_name
            await db.commit()

    user.last_login_at = datetime.utcnow()
    user.last_login_source = "crm_sso"
    await db.commit()

    return await _token_response(user, db, is_new_user=is_new)


# ═════════════════════════════════════════════════════════════════════════════
# 5. 用户信息
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/me", response_model=UserProfile)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    plan = await _get_effective_plan(current_user, db)
    # Build a response dict so we can inject subscription_plan
    profile = UserProfile.model_validate(current_user)
    profile.subscription_plan = plan
    return profile


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """首次使用软引导信息提交（行业/角色/姓名，全部可选）。"""
    changed = False
    if body.name is not None:
        current_user.name = body.name
        changed = True
    if body.industry is not None:
        current_user.industry = body.industry
        changed = True
    if body.role is not None:
        current_user.role = body.role
        changed = True
    if changed:
        current_user.recalculate_completeness()
        await db.commit()
        await db.refresh(current_user)
    return current_user
