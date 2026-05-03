from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


# ── SMS ───────────────────────────────────────────────────────────────────────

def _normalize_phone(v: str) -> str:
    """统一手机号格式：去掉前导空格，中国大陆号加 86 前缀。"""
    v = v.strip()
    if not v.startswith("+"):
        if not v.startswith("86"):
            v = "86" + v.lstrip("0")
    if len(v.lstrip("+")) < 10:
        raise ValueError("手机号格式不正确")
    return v


class PhoneSendCodeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        return _normalize_phone(v)


class PhoneLoginRequest(BaseModel):
    phone: str
    code: str
    channel: Optional[str] = None   # utm_source 渠道来源

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        return _normalize_phone(v)


# ── WeChat QR ─────────────────────────────────────────────────────────────────

class WechatQrcodeResponse(BaseModel):
    qrcode_url: str
    session_key: str
    expires_in: int


class WechatQrcodeStatusResponse(BaseModel):
    status: str                                 # pending | scanned | confirmed | expired
    token_response: Optional["TokenResponse"] = None


class WechatCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None                # session_key，用于通知轮询端


# ── Email ─────────────────────────────────────────────────────────────────────

class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    company_name: Optional[str] = None         # 改为可选（以前是必填）

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        return v


class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None


# ── Token / User ─────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    tenant_id: int
    role: str
    is_new_user: bool = False
    profile_completeness: int = 0


class UserProfile(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    tenant_id: int
    avatar_url: Optional[str] = None
    industry: Optional[str] = None
    profile_completeness: int = 0
    register_source: str = "web"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Backward-compat aliases ───────────────────────────────────────────────────
# Old code that imported RegisterRequest / LoginRequest still works.

class RegisterRequest(EmailRegisterRequest):
    """Backward-compat alias → EmailRegisterRequest."""
    company_name: str = ""   # 旧代码可能传必填 company_name，保持兼容


class LoginRequest(EmailLoginRequest):
    """Backward-compat alias → EmailLoginRequest."""


# Allow forward-reference in WechatQrcodeStatusResponse
WechatQrcodeStatusResponse.model_rebuild()
