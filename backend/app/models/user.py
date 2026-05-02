from datetime import datetime
from sqlalchemy import BigInteger, String, SmallInteger, DateTime, Index, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "pc_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Standalone mode login
    email: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str | None] = mapped_column(String(256))

    # Common fields
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    avatar_url: Mapped[str | None] = mapped_column(String(512))

    # CRM integration fields
    external_user_id: Mapped[str | None] = mapped_column(String(128))
    sso_provider: Mapped[str | None] = mapped_column(String(32))

    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uk_tenant_email"),
        UniqueConstraint("tenant_id", "phone", name="uk_tenant_phone"),
        UniqueConstraint("tenant_id", "sso_provider", "external_user_id", name="uk_external"),
        Index("idx_tenant_user", "tenant_id"),
    )
