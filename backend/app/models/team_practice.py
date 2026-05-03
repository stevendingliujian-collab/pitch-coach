"""
多人组队排练模型

team_practice_session: 一场多人接力排练会话（绑定到某个述标任务）
team_practice_participant: 参与者记录（绑定到某个 Rehearsal）
"""
from datetime import datetime
from sqlalchemy import BigInteger, String, SmallInteger, Integer, DateTime, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TeamPracticeSession(Base):
    __tablename__ = "team_practice_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    pitch_task_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # user_id

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Roles: list of dicts {role: str, description: str, assigned_user_id?: int}
    roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # status: 0=draft, 1=open (accepting participants), 2=in_progress, 3=completed
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    # aggregate scores set when session completes
    avg_score: Mapped[float | None] = mapped_column(nullable=True)
    total_score: Mapped[float | None] = mapped_column(nullable=True)
    feedback: Mapped[list | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TeamPracticeParticipant(Base):
    __tablename__ = "team_practice_participant"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    role_index: Mapped[int] = mapped_column(Integer, nullable=False)  # index into session.roles[]
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Linked rehearsal (set when participant submits their turn)
    rehearsal_id: Mapped[int | None] = mapped_column(BigInteger)
    # status: 0=joined, 1=submitted
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    score: Mapped[float | None] = mapped_column(nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text)

    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
