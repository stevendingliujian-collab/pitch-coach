"""
Authorization helpers — pure decision functions with no I/O, so they can be
unit-tested in isolation and reused across routes.
"""
from __future__ import annotations

# Roles a user may self-assign through the onboarding / profile flow. These are
# job descriptors only. They deliberately EXCLUDE the RBAC privilege roles
# (owner / admin / manager), which grant elevated permissions and must never be
# writable by the user — otherwise `PUT /auth/profile {"role":"admin"}` would be
# a self-service privilege escalation.
ONBOARDING_ROLES: frozenset[str] = frozenset(
    {"pre_sales", "technical", "sales_mgr", "pm", "presenter"}
)

# Roles that carry elevated privileges and must not be downgraded by the
# onboarding flow.
PRIVILEGED_ROLES: frozenset[str] = frozenset({"owner", "admin", "manager"})


class InvalidRoleError(ValueError):
    """Raised when a requested onboarding role is not an allowed job role."""


def resolve_onboarding_role(current_role: str, requested_role: str) -> str | None:
    """Decide the role to persist for a profile/onboarding update.

    Returns the new role string to store, or None if the role should be left
    unchanged (already-privileged users are never downgraded here). Raises
    InvalidRoleError if `requested_role` is not an allowed onboarding role —
    this is what blocks self-service privilege escalation.
    """
    if requested_role not in ONBOARDING_ROLES:
        raise InvalidRoleError(requested_role)
    if current_role in PRIVILEGED_ROLES:
        return None
    return requested_role
