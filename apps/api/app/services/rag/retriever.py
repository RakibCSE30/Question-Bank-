from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.documents import Document, DocumentChunk
from app.services.ai.base import EmbeddingProvider
from app.services.ai.registry import get_embedding_provider
from app.services.ingestion.bengali_unicode import normalize_bengali_nfc
from app.services.rag.vector_store import ChunkVectorPoint, QdrantVectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    source_type: str
    page_number: int
    heading_path: str | None
    content_nfc: str
    score: float
    usable_for_generation: bool


def index_document_chunks(
    db: Session,
    doc: Document,
    *,
    usable_for_generation: bool,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> int:
    """Embed all chunks for a document and upsert them into Qdrant with metadata payloads."""
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
    )
    if not chunks:
        return 0

    embedder = embedding_provider or get_embedding_provider()
    store = vector_store or QdrantVectorStore()

    texts = [c.content_nfc for c in chunks]
    vectors = embedder.embed_texts(texts)

    store.delete_document_vectors(doc.id)

    points: list[ChunkVectorPoint] = []
    for chunk, vec in zip(chunks, vectors, strict=True):
        point_id = str(chunk.id)
        chunk.vector_point_id = point_id
        points.append(
            ChunkVectorPoint(
                point_id=point_id,
                chunk_id=str(chunk.id),
                document_id=str(doc.id),
                document_title=doc.title,
                subject_id=str(doc.subject_id),
                chapter_id=str(doc.chapter_id) if doc.chapter_id else None,
                page_number=chunk.page_number,
                heading_path=chunk.heading_path,
                source_type=doc.source_type,
                usable_for_generation=usable_for_generation,
                vector=vec,
            )
        )

    store.upsert_chunks(points)
    db.commit()
    return len(points)


def retrieve_relevant_chunks(
    db: Session,
    *,
    query: str,
    subject_id: uuid.UUID,
    chapter_id: uuid.UUID | None = None,
    top_k: int = 5,
    usable_only: bool = True,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: QdrantVectorStore | None = None,
) -> list[RetrievedChunk]:
    normalized_query = normalize_bengali_nfc(query)
    if not normalized_query:
        return []

    embedder = embedding_provider or get_embedding_provider()
    store = vector_store or QdrantVectorStore()

    query_vec = embedder.embed_texts([normalized_query])[0]
    hits = store.search_chunks(
        query_vector=query_vec,
        subject_id=subject_id,
        chapter_id=chapter_id,
        top_k=top_k,
        usable_only=usable_only,
    )
    if not hits:
        return []

    chunk_ids = [uuid.UUID(h.chunk_id) for h in hits]
    rows = db.execute(
        select(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.id.in_(chunk_ids))
    ).all()
    chunk_map = {str(chunk.id): (chunk, doc) for chunk, doc in rows}

    results: list[RetrievedChunk] = []
    for hit in hits:
        pair = chunk_map.get(hit.chunk_id)
        if not pair:
            continue
        chunk, doc = pair
        if usable_only and not (
            doc.ingestion_status == "COMPLETED"
            or (doc.ingestion_status == "FLAGGED" and doc.admin_confirmed_low_quality)
        ):
            continue
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                document_title=doc.title,
                source_type=doc.source_type,
                page_number=chunk.page_number,
                heading_path=chunk.heading_path,
                content_nfc=chunk.content_nfc,
                score=round(hit.score, 4),
                usable_for_generation=hit.usable_for_generation,
            )
        )
    return results
