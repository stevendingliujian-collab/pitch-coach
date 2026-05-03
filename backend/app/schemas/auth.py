from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    company_name: str
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    tenant_id: int
    role: str


class UserProfile(BaseModel):
    id: int
    name: str
    email: str | None
    role: str
    tenant_id: int
    avatar_url: str | None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
