"""
Embedding service: DashScope text-embedding-v3 API + Qdrant vector store operations.

Architecture:
  - Embeddings: DashScope compatible-mode API (OpenAI-style), model text-embedding-v3, 1024-dim
  - Vector store: Qdrant (single container, no dependencies)
  - Collection name: "knowledge_chunks" (one collection for all tenants; tenant_id in payload)
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, TYPE_CHECKING

import httpx

from app.core.config import get_settings

# Lazy imports for qdrant_client — imported at first use so the app starts
# even when the package is not yet installed locally.
try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
        ScoredPoint,
    )
    _QDRANT_AVAILABLE = True
except ImportError:
    _QDRANT_AVAILABLE = False
    AsyncQdrantClient = None  # type: ignore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLLECTION_NAME = "knowledge_chunks"
BATCH_SIZE = 50          # max chunks per embedding API call
SEARCH_TOP_K = 20        # candidates before RRF merge


# ---------------------------------------------------------------------------
# Embedding API helpers
# ---------------------------------------------------------------------------

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts using DashScope text-embedding-v3 (OpenAI-compatible).
    Returns a list of 1024-dim float vectors, same order as input.
    Batches automatically if len(texts) > BATCH_SIZE.
    """
    if not texts:
        return []

    settings = get_settings()
    all_vectors: list[list[float]] = []

    # Process in batches
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vectors = await _embed_batch(batch, settings)
        all_vectors.extend(vectors)

    return all_vectors


async def _embed_batch(texts: list[str], settings) -> list[list[float]]:
    """Call embedding API for one batch (<= BATCH_SIZE)."""
    url = f"{settings.embedding_base_url}/embeddings"
    api_key = settings.embedding_api_key or settings.llm_api_key
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.embedding_model,
        "input": texts,
        "encoding_format": "float",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # OpenAI-compatible: data.data[i].embedding
    items: list[dict] = data["data"]
    # Sort by index to guarantee order
    items.sort(key=lambda x: x["index"])
    return [item["embedding"] for item in items]


# ---------------------------------------------------------------------------
# Qdrant client singleton
# ---------------------------------------------------------------------------

_qdrant_client: AsyncQdrantClient | None = None


def get_qdrant_client():
    global _qdrant_client
    if not _QDRANT_AVAILABLE:
        raise RuntimeError(
            "qdrant-client is not installed. Run: pip install qdrant-client==1.9.1"
        )
    if _qdrant_client is None:
        settings = get_settings()
        qdrant_url = settings.qdrant_url
        # Support in-memory mode for testing (QDRANT_URL=:memory:)
        if qdrant_url == ":memory:":
            _qdrant_client = AsyncQdrantClient(location=":memory:")
        else:
            _qdrant_client = AsyncQdrantClient(url=qdrant_url)
    return _qdrant_client


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

async def ensure_collection() -> None:
    """Create the Qdrant collection if it doesn't exist."""
    if not _QDRANT_AVAILABLE:
        raise RuntimeError("qdrant-client is not installed. Run: pip install qdrant-client==1.9.1")

    from qdrant_client.models import VectorParams, Distance  # re-import for type safety

    client = get_qdrant_client()
    settings = get_settings()

    existing = await client.get_collections()
    names = [c.name for c in existing.collections]

    if COLLECTION_NAME not in names:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.embedding_dim,
                distance=Distance.COSINE,
            ),
        )


# ---------------------------------------------------------------------------
# Upsert / delete
# ---------------------------------------------------------------------------

async def upsert_chunks(
    chunk_records: list[dict[str, Any]],
) -> list[str]:
    """
    Embed chunk texts and upsert into Qdrant.

    Each record in chunk_records must have:
        - chunk_id (int)         DB id of knowledge_chunk
        - doc_id (int)
        - tenant_id (int)
        - content (str)
        - heading (str | None)
        - page_number (int | None)
        - content_type (str)

    Returns list of Qdrant point IDs (UUIDs as strings) in the same order.
    """
    await ensure_collection()

    texts = [r["content"] for r in chunk_records]
    vectors = await embed_texts(texts)

    from qdrant_client.models import PointStruct  # lazy import

    points: list = []
    point_ids: list[str] = []

    for record, vector in zip(chunk_records, vectors):
        point_id = str(uuid.uuid4())
        point_ids.append(point_id)
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "chunk_id": record["chunk_id"],
                    "doc_id": record["doc_id"],
                    "tenant_id": record["tenant_id"],
                    "content": record["content"],
                    "heading": record.get("heading"),
                    "page_number": record.get("page_number"),
                    "content_type": record.get("content_type", "text"),
                },
            )
        )

    client = get_qdrant_client()
    await client.upsert(collection_name=COLLECTION_NAME, points=points)

    return point_ids


async def delete_document_vectors(doc_id: int) -> None:
    """Delete all Qdrant points belonging to a document."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue  # lazy import

    client = get_qdrant_client()
    await client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )


# ---------------------------------------------------------------------------
# Vector similarity search
# ---------------------------------------------------------------------------

async def vector_search(
    query: str,
    tenant_id: int,
    top_k: int = SEARCH_TOP_K,
    doc_type: str | None = None,
    industry: str | None = None,
) -> list[dict[str, Any]]:
    """
    Embed query and search Qdrant for similar chunks within tenant scope.

    Returns list of dicts with keys:
        chunk_id, doc_id, score, content, heading, page_number, content_type
    Sorted by descending score.
    """
    await ensure_collection()
    client = get_qdrant_client()

    query_vector = (await embed_texts([query]))[0]

    from qdrant_client.models import Filter, FieldCondition, MatchValue  # lazy import

    # Build filter conditions
    must_conditions = [
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
    ]

    from qdrant_client.models import QueryRequest  # noqa: F401 — version compat check

    response = await client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        query_filter=Filter(must=must_conditions),
        with_payload=True,
    )

    hits = []
    for r in response.points:
        payload = r.payload or {}
        hits.append(
            {
                "chunk_id": payload.get("chunk_id"),
                "doc_id": payload.get("doc_id"),
                "score": r.score,
                "content": payload.get("content", ""),
                "heading": payload.get("heading"),
                "page_number": payload.get("page_number"),
                "content_type": payload.get("content_type", "text"),
            }
        )

    return hits
