from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_roles
from app.db.models.curriculum import SyllabusItem
from app.db.models.documents import Document
from app.db.models.logs import AuditLog
from app.db.models.users import User
from app.db.session import get_db
from app.services.ai.exceptions import AIConfigurationError, AIProviderError
from app.services.ai.registry import get_ai_configuration_status
from app.services.analysis.syllabus_analyzer import analyze_syllabus_document
from app.services.rag.retriever import retrieve_relevant_chunks
from app.workers.tasks import is_document_usable_for_generation

router = APIRouter(tags=["ai-rag-syllabus"])


class AIStatusResponse(BaseModel):
    llm_provider: str
    generation_model: str
    verification_model: str
    verification_temperature: float
    embedding_provider: str
    embedding_model: str
    bge_m3_model: str
    openai_api_key_configured: bool
    bge_m3_installed: bool
    llm_ready: bool
    embedding_ready: bool


class RAGRetrieveRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    subject_id: uuid.UUID
    chapter_id: uuid.UUID | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    usable_only: bool = True


class RetrievedChunkOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    source_type: str
    page_number: int
    heading_path: str | None
    content_nfc: str
    score: float
    usable_for_generation: bool


class RAGRetrieveResponse(BaseModel):
    query: str
    total: int
    items: list[RetrievedChunkOut]


class SyllabusAnalyzeRequest(BaseModel):
    document_id: uuid.UUID


class SyllabusItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    chapter_id: uuid.UUID | None
    topic_bn: str
    topic_en: str | None
    weight_percentage: float
    priority: str
    priority_reason: str | None
    source_reference: str | None
    created_at: datetime


@router.get("/ai/status", response_model=AIStatusResponse)
def ai_status(_user: User = Depends(require_roles("ADMIN", "REVIEWER"))) -> AIStatusResponse:
    return AIStatusResponse(**get_ai_configuration_status())


@router.post("/rag/retrieve", response_model=RAGRetrieveResponse)
def rag_retrieve(
    payload: RAGRetrieveRequest,
    _user: User = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
) -> RAGRetrieveResponse:
    try:
        chunks = retrieve_relevant_chunks(
            db,
            query=payload.query,
            subject_id=payload.subject_id,
            chapter_id=payload.chapter_id,
            top_k=payload.top_k,
            usable_only=payload.usable_only,
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector retrieval failed: {type(exc).__name__}",
        ) from exc

    return RAGRetrieveResponse(
        query=payload.query,
        total=len(chunks),
        items=[
            RetrievedChunkOut(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=c.document_title,
                source_type=c.source_type,
                page_number=c.page_number,
                heading_path=c.heading_path,
                content_nfc=c.content_nfc,
                score=c.score,
                usable_for_generation=c.usable_for_generation,
            )
            for c in chunks
        ],
    )


@router.post("/admin/syllabus/analyze", response_model=list[SyllabusItemOut])
def analyze_syllabus(
    payload: SyllabusAnalyzeRequest,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> list[SyllabusItemOut]:
    doc = db.scalar(select(Document).where(Document.id == payload.document_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if not is_document_usable_for_generation(doc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is FLAGGED or incomplete and cannot be analyzed until confirmed by Admin.",
        )

    try:
        items = analyze_syllabus_document(db, document=doc, triggered_by=admin.id)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="SYLLABUS_ANALYZED",
            entity_type="document",
            entity_id=doc.id,
            after_state={"extracted_items": len(items)},
        )
    )
    db.commit()

    return [
        SyllabusItemOut(
            id=row.id,
            subject_id=row.subject_id,
            chapter_id=row.chapter_id,
            topic_bn=row.topic_bn,
            topic_en=row.topic_en,
            weight_percentage=float(row.weight_percentage),
            priority=row.priority,
            priority_reason=row.priority_reason,
            source_reference=row.source_reference,
            created_at=row.created_at,
        )
        for row in items
    ]


@router.get("/syllabus", response_model=list[SyllabusItemOut])
def list_syllabus_items(
    subject_id: uuid.UUID = Query(...),
    chapter_id: uuid.UUID | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SyllabusItemOut]:
    stmt = select(SyllabusItem).where(SyllabusItem.subject_id == subject_id)
    if chapter_id is not None:
        stmt = stmt.where(SyllabusItem.chapter_id == chapter_id)
    rows = db.scalars(stmt.order_by(SyllabusItem.created_at.asc())).all()
    return [
        SyllabusItemOut(
            id=row.id,
            subject_id=row.subject_id,
            chapter_id=row.chapter_id,
            topic_bn=row.topic_bn,
            topic_en=row.topic_en,
            weight_percentage=float(row.weight_percentage),
            priority=row.priority,
            priority_reason=row.priority_reason,
            source_reference=row.source_reference,
            created_at=row.created_at,
        )
        for row in rows
    ]
