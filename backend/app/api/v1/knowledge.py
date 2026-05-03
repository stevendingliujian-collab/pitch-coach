"""P1 知识库 API.

Endpoints:
  POST   /knowledge/documents/upload-url   获取 MinIO 预签名上传 URL
  POST   /knowledge/documents              注册文档 + 触发嵌入任务
  GET    /knowledge/documents              列出文档（分页）
  GET    /knowledge/documents/{id}         获取单个文档
  DELETE /knowledge/documents/{id}         删除文档 + 向量
  POST   /knowledge/search                 混合检索
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import get_presigned_upload_url, get_presigned_download_url
from app.models.knowledge import KnowledgeDocument
from app.models.user import User

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class UploadUrlRequest(BaseModel):
    file_name: str
    content_type: str = "application/octet-stream"


class UploadUrlResponse(BaseModel):
    upload_url: str
    object_key: str


class RegisterDocumentRequest(BaseModel):
    object_key: str      # from upload-url response
    file_name: str
    file_size: Optional[int] = None
    doc_type: str        # bid_doc/lost_bid/whitepaper/case_study/rubric_template/company_profile/competitor_card/glossary
    industry: Optional[str] = None
    project_type: Optional[str] = None
    tags: Optional[list[str]] = None
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    tenant_id: int
    doc_type: str
    file_name: str
    file_url: str
    file_size: Optional[int]
    chunk_count: int
    embedding_status: int
    embedding_status_label: str
    industry: Optional[str]
    project_type: Optional[str]
    tags: Optional[list]
    description: Optional[str]
    uploaded_by: int
    created_at: str

    model_config = {"from_attributes": True}


_STATUS_LABELS = {0: "待处理", 1: "处理中", 2: "已完成", 3: "失败"}


def _doc_to_response(doc: KnowledgeDocument) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        tenant_id=doc.tenant_id,
        doc_type=doc.doc_type,
        file_name=doc.file_name,
        file_url=doc.file_url,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        embedding_status=doc.embedding_status,
        embedding_status_label=_STATUS_LABELS.get(doc.embedding_status, "未知"),
        industry=doc.industry,
        project_type=doc.project_type,
        tags=doc.tags,
        description=doc.description,
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at.isoformat() if doc.created_at else "",
    )


class SearchRequest(BaseModel):
    query: str
    top_n: int = 8
    doc_type: Optional[str] = None
    industry: Optional[str] = None


class SearchHit(BaseModel):
    chunk_id: Optional[int]
    doc_id: Optional[int]
    doc_name: Optional[str] = None
    rrf_score: float
    content: str
    heading: Optional[str]
    page_number: Optional[int]
    content_type: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/documents/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    req: UploadUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """Get a presigned MinIO URL for direct client-side upload."""
    # Sanitise filename to avoid path traversal
    safe_name = req.file_name.replace("/", "_").replace("..", "_")
    object_key = f"{current_user.tenant_id}/knowledge/{uuid.uuid4().hex}_{safe_name}"
    upload_url = get_presigned_upload_url(object_key, expires_seconds=3600)
    return UploadUrlResponse(upload_url=upload_url, object_key=object_key)


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def register_document(
    req: RegisterDocumentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register an uploaded document and trigger the ingestion (embed) pipeline.
    The file should already be uploaded to MinIO via the upload-url endpoint.
    """
    doc = KnowledgeDocument(
        tenant_id=current_user.tenant_id,
        doc_type=req.doc_type,
        file_name=req.file_name,
        file_url=req.object_key,
        file_size=req.file_size,
        industry=req.industry,
        project_type=req.project_type,
        tags=req.tags,
        description=req.description,
        uploaded_by=current_user.id,
        embedding_status=0,  # pending
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Trigger async ingestion task
    from app.workers.tasks import ingest_document_task
    ingest_document_task.delay(doc.id)

    return _doc_to_response(doc)


@router.get("/documents", response_model=dict)
async def list_documents(
    doc_type: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    embedding_status: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List knowledge documents for the current tenant."""
    q = select(KnowledgeDocument).where(
        KnowledgeDocument.tenant_id == current_user.tenant_id
    )
    if doc_type:
        q = q.where(KnowledgeDocument.doc_type == doc_type)
    if industry:
        q = q.where(KnowledgeDocument.industry == industry)
    if embedding_status is not None:
        q = q.where(KnowledgeDocument.embedding_status == embedding_status)

    # Count total
    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    # Paginate
    q = q.order_by(KnowledgeDocument.created_at.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    docs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_doc_to_response(d) for d in docs],
    }


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc or doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_response(doc)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc or doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.services.knowledge_service import delete_document as svc_delete
    await svc_delete(doc_id, db)


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    req: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hybrid search (vector + keyword, RRF fusion) over the tenant's knowledge base.
    """
    if not req.query.strip():
        return SearchResponse(hits=[], total=0)

    from app.services.knowledge_service import hybrid_search

    hits = await hybrid_search(
        query=req.query,
        tenant_id=current_user.tenant_id,
        db=db,
        top_n=req.top_n,
        doc_type=req.doc_type,
        industry=req.industry,
    )

    # Enrich with doc file_name
    doc_ids = list({h["doc_id"] for h in hits if h.get("doc_id")})
    doc_names: dict[int, str] = {}
    if doc_ids:
        docs_result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id.in_(doc_ids))
        )
        for d in docs_result.scalars().all():
            doc_names[d.id] = d.file_name

    search_hits = [
        SearchHit(
            chunk_id=h.get("chunk_id"),
            doc_id=h.get("doc_id"),
            doc_name=doc_names.get(h.get("doc_id")),
            rrf_score=h.get("rrf_score", 0.0),
            content=h.get("content", ""),
            heading=h.get("heading"),
            page_number=h.get("page_number"),
            content_type=h.get("content_type", "text"),
        )
        for h in hits
    ]

    return SearchResponse(hits=search_hits, total=len(search_hits))
