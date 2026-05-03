"""
Feature Gate Middleware

Intercepts POST requests to quota-gated endpoints.
Returns HTTP 402 with a structured upgrade trigger payload when quota is exceeded.

Gated endpoints (free plan):
  POST /api/v1/pitch-tasks          → ppt_uploads   (limit 3/month)
  POST /api/v1/rehearsals           → rehearsals    (limit 5/month)
  POST /api/v1/narrations/generate  → narration_pages (first 3 pages only)

Response shape on 402:
  {
    "detail": "quota_exceeded",
    "feature": "ppt_uploads",
    "used": 3,
    "limit": 3,
    "trigger_id": "T2",          # conversion trigger ID for frontend banner
    "label": "PPT 上传（免费版 3 份/月）",
    "message": "..."
  }
"""
import json
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.models.tenant import Tenant
from app.services.quota_service import check_quota, FEATURE_LABELS, get_gated_routes
from sqlalchemy import select

# Load gated routes from feature registry (YAML-driven)
# Falls back to hardcoded routes if registry is empty.
_registry_routes = get_gated_routes()
GATED_ROUTES: list[tuple[str, str, str, str]] = _registry_routes or [
    ("POST", "/api/v1/pitch-tasks",         "ppt_uploads",     "T2"),
    ("POST", "/api/v1/rehearsals",          "rehearsals",      "T2"),
    ("POST", "/api/v1/narrations/generate", "narration_pages", "T1"),
]


def _match_route(method: str, path: str) -> tuple[str, str] | None:
    for m, prefix, feature, trigger_id in GATED_ROUTES:
        if method == m and path.startswith(prefix):
            return feature, trigger_id
    return None


class FeatureGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        match = _match_route(request.method, request.url.path)
        if not match:
            return await call_next(request)

        feature, trigger_id = match

        # Extract bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header[7:]
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
            tenant_id = int(payload["tenant_id"])
        except Exception:
            return await call_next(request)

        # Check quota in a short-lived session
        async with AsyncSessionLocal() as db:
            user_row = await db.get(User, user_id)
            if not user_row:
                return await call_next(request)

            # Determine plan type from tenant
            tenant_row = await db.get(Tenant, tenant_id)
            plan_type = getattr(tenant_row, "plan_type", "free") if tenant_row else "free"

            allowed, used, limit = await check_quota(
                feature, user_row, db, plan_type=plan_type
            )

        if not allowed:
            label = FEATURE_LABELS.get(feature, feature)
            return JSONResponse(
                status_code=402,
                content={
                    "detail": "quota_exceeded",
                    "feature": feature,
                    "used": used,
                    "limit": limit,
                    "trigger_id": trigger_id,
                    "label": label,
                    "message": f"已达到本月{label}上限，升级专业版即可无限使用。",
                },
            )

        return await call_next(request)
