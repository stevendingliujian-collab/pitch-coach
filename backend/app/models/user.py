from datetime import datetime
from sqlalchemy import BigInteger, String, SmallInteger, DateTime, Index, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "pc_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # ── 基础凭证 ──────────────────────────────────────────────────────────────
    email: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str | None] = mapped_column(String(256))

    # ── 基础信息（name 可为空，微信/手机注册时渐进收集）────────────────────────
    name: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    # ── 渐进收集 ──────────────────────────────────────────────────────────────
    industry: Mapped[str | None] = mapped_column(String(64))           # 行业
    register_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="web"
    )   # web / phone / wechat / wecom / feishu / crm_sso
    register_channel: Mapped[str | None] = mapped_column(String(64))   # utm_source
    profile_completeness: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=10
    )
    last_login_source: Mapped[str | None] = mapped_column(String(32))

    # ── 微信 ──────────────────────────────────────────────────────────────────
    wechat_unionid: Mapped[str | None] = mapped_column(String(64))
    wechat_openid_web: Mapped[str | None] = mapped_column(String(64))  # PC 扫码
    wechat_openid_mp: Mapped[str | None] = mapped_column(String(64))   # 小程序（P3）
    wechat_openid_oa: Mapped[str | None] = mapped_column(String(64))   # 公众号

    # ── 企业微信（P1） ────────────────────────────────────────────────────────
    wecom_userid: Mapped[str | None] = mapped_column(String(64))
    wecom_corpid: Mapped[str | None] = mapped_column(String(64))

    # ── 飞书（P1） ────────────────────────────────────────────────────────────
    feishu_userid: Mapped[str | None] = mapped_column(String(64))
    feishu_tenant_key: Mapped[str | None] = mapped_column(String(64))

    # ── 钉钉（P2） ────────────────────────────────────────────────────────────
    dingtalk_userid: Mapped[str | None] = mapped_column(String(64))

    # ── CRM SSO ──────────────────────────────────────────────────────────────
    crm_user_id: Mapped[str | None] = mapped_column(String(128))
    # 保留 sso_provider / external_user_id 向后兼容
    external_user_id: Mapped[str | None] = mapped_column(String(128))
    sso_provider: Mapped[str | None] = mapped_column(String(32))

    # ── 状态 ──────────────────────────────────────────────────────────────────
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uk_tenant_email"),
        UniqueConstraint("tenant_id", "phone", name="uk_tenant_phone"),
        UniqueConstraint("tenant_id", "sso_provider", "external_user_id", name="uk_external"),
        Index("idx_tenant_user", "tenant_id"),
    )

    # ── 计算属性 ──────────────────────────────────────────────────────────────
    @property
    def display_name(self) -> str:
        """展示名：优先用 name，其次手机号脱敏，最后 user_{id}"""
        if self.name:
            return self.name
        if self.phone:
            return self.phone[:3] + "****" + self.phone[-4:]
        return f"用户{self.id}"

    def recalculate_completeness(self) -> int:
        """
        计算档案完整度（0-100）。
        name 15 + phone 20 + avatar 5 + industry 15 + role(非member) 10
        + company(非默认) 20 + email 10 + 企业IM绑定 5
        """
        score = 0
        if self.name:                               score += 15
        if self.phone:                              score += 20
        if self.avatar_url:                         score += 5
        if self.industry:                           score += 15
        if self.role and self.role != "member":     score += 10
        if self.email:                              score += 10
        if any([self.wecom_userid, self.feishu_userid, self.dingtalk_userid]):
            score += 5
        # 公司名由 Tenant 维护，加分逻辑在调用侧处理（+20 if tenant.name != default）
        self.profile_completeness = score
        return score
