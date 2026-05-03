from datetime import datetime
from sqlalchemy import (BigInteger, String, SmallInteger, Integer, DateTime,
                        Text, JSON, Numeric, ForeignKey, Index, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 0=pending 1=processing 2=done 3=failed
    embedding_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    industry: Mapped[str | None] = mapped_column(String(64))
    project_type: Mapped[str | None] = mapped_column(String(64))
    tags: Mapped[list | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text)

    uploaded_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_kb_tenant_type", "tenant_id", "doc_type"),
        Index("idx_kb_tenant_industry", "tenant_id", "industry"),
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_document.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(16), nullable=False, default="text")
    heading: Mapped[str | None] = mapped_column(String(256))
    page_number: Mapped[int | None] = mapped_column(Integer)
    vector_id: Mapped[str | None] = mapped_column(String(64))  # Qdrant point ID

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_doc", "doc_id"),
        Index("idx_chunk_tenant", "tenant_id"),
    )


class GoldenScript(Base):
    __tablename__ = "golden_script"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rehearsal_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("rehearsal.id", ondelete="SET NULL"), nullable=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_clip_url: Mapped[str | None] = mapped_column(String(512))
    start_sec: Mapped[float | None] = mapped_column(Numeric(8, 2))
    end_sec: Mapped[float | None] = mapped_column(Numeric(8, 2))
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    marked_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vector_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_golden_tenant", "tenant_id"),
    )
