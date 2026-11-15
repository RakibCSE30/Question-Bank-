from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import require_roles
from app.db.models.curriculum import Chapter, Subject
from app.db.models.documents import Document, DocumentChunk
from app.db.models.logs import AuditLog
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.documents import (
    DocumentChunkOut,
    DocumentDetailOut,
    DocumentListResponse,
    DocumentOut,
    SourceType,
)
from app.services.ingestion.validator import compute_sha256, validate_upload_metadata
from app.workers.tasks import ingest_document_task, is_document_usable_for_generation

router = APIRouter(prefix="/admin/documents", tags=["documents"])


def _to_document_out(doc: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        uploaded_by=doc.uploaded_by,
        subject_id=doc.subject_id,
        chapter_id=doc.chapter_id,
        title=doc.title,
        source_type=doc.source_type,
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        sha256_hash=doc.sha256_hash,
        extraction_method=doc.extraction_method,
        legacy_encoding_detected=doc.legacy_encoding_detected,
        extraction_quality_score=float(doc.extraction_quality_score)
        if doc.extraction_quality_score is not None
        else None,
        admin_confirmed_low_quality=doc.admin_confirmed_low_quality,
        usable_for_generation=is_document_usable_for_generation(doc),
        page_count=doc.page_count,
        ingestion_status=doc.ingestion_status,
        error_message=doc.error_message,
        chunk_count=chunk_count,
        created_at=doc.created_at,
    )


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    subject_id: uuid.UUID = Form(...),
    title: str = Form(..., min_length=2, max_length=500),
    source_type: SourceType = Form(...),
    chapter_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> DocumentOut:
    settings = get_settings()

    subject = db.scalar(select(Subject).where(Subject.id == subject_id))
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    if chapter_id is not None:
        chapter = db.scalar(
            select(Chapter).where(Chapter.id == chapter_id, Chapter.subject_id == subject_id)
        )
        if chapter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chapter not found for the selected subject.",
            )

    raw_bytes = await file.read()
    ext = validate_upload_metadata(
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(raw_bytes),
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
    )

    sha256_hex = compute_sha256(raw_bytes)
    existing = db.scalar(select(Document).where(Document.sha256_hash == sha256_hex))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate file detected (matches existing document '{existing.title}').",
        )

    doc_id = uuid.uuid4()
    storage_dir = Path(settings.STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    target_path = storage_dir / f"{doc_id}{ext}"
    target_path.write_bytes(raw_bytes)

    initial_method = {
        ".pdf": "PYMUPDF",
        ".docx": "DOCX",
        ".txt": "TXT",
    }.get(ext, "IMAGE_OCR")

    doc = Document(
        id=doc_id,
        uploaded_by=admin.id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        title=title.strip(),
        source_type=source_type,
        file_name=file.filename or f"{doc_id}{ext}",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(raw_bytes),
        sha256_hash=sha256_hex,
        storage_path=str(target_path),
        extraction_method=initial_method,
        ingestion_status="PENDING",
    )
    db.add(doc)
    db.flush()

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="DOCUMENT_UPLOADED",
            entity_type="document",
            entity_id=doc.id,
            after_state={"title": doc.title, "source_type": doc.source_type, "sha256": sha256_hex},
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(doc)

    # Dispatch async Celery OCR/extraction job
    ingest_document_task.delay(str(doc.id), False)

    return _to_document_out(doc, chunk_count=0)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    subject_id: uuid.UUID | None = Query(default=None),
    ingestion_status: str | None = Query(default=None),
    usable_only: bool = Query(default=False),
    _user: User = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    stmt = select(Document).order_by(Document.created_at.desc())
    if subject_id is not None:
        stmt = stmt.where(Document.subject_id == subject_id)
    if ingestion_status is not None:
        stmt = stmt.where(Document.ingestion_status == ingestion_status)

    docs = list(db.scalars(stmt).all())
    if usable_only:
        docs = [d for d in docs if is_document_usable_for_generation(d)]

    counts_rows = db.execute(
        select(DocumentChunk.document_id, func.count(DocumentChunk.id)).group_by(DocumentChunk.document_id)
    ).all()
    chunk_counts = {row[0]: int(row[1]) for row in counts_rows}

    items = [_to_document_out(d, chunk_counts.get(d.id, 0)) for d in docs]
    return DocumentListResponse(items=items, total=len(items))


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document_detail(
    document_id: uuid.UUID,
    _user: User = Depends(require_roles("ADMIN", "REVIEWER")),
    db: Session = Depends(get_db),
) -> DocumentDetailOut:
    doc = db.scalar(select(Document).where(Document.id == document_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
    )
    base = _to_document_out(doc, chunk_count=len(chunks))
    return DocumentDetailOut(
        **base.model_dump(),
        chunks=[
            DocumentChunkOut(
                id=c.id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                heading_path=c.heading_path,
                content_nfc=c.content_nfc,
                token_count=c.token_count,
                extraction_confidence=float(c.extraction_confidence)
                if c.extraction_confidence is not None
                else None,
                created_at=c.created_at,
            )
            for c in chunks
        ],
    )


@router.post("/{document_id}/confirm", response_model=DocumentOut)
def confirm_flagged_document(
    document_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = db.scalar(select(Document).where(Document.id == document_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.ingestion_status != "FLAGGED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only FLAGGED documents require low-quality confirmation.",
        )

    doc.admin_confirmed_low_quality = True
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="FLAGGED_DOCUMENT_CONFIRMED",
            entity_type="document",
            entity_id=doc.id,
            before_state={"admin_confirmed_low_quality": False},
            after_state={"admin_confirmed_low_quality": True},
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(doc)

    try:
        from app.services.rag.vector_store import QdrantVectorStore

        QdrantVectorStore().update_document_usability(doc.id, True)
    except Exception:
        pass

    chunk_count = db.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    ) or 0
    return _to_document_out(doc, int(chunk_count))


@router.post("/{document_id}/reprocess-ocr", response_model=DocumentOut)
def reprocess_document_ocr(
    document_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> DocumentOut:
    doc = db.scalar(select(Document).where(Document.id == document_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc.ingestion_status = "PENDING"
    doc.admin_confirmed_low_quality = False
    doc.error_message = None
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="DOCUMENT_OCR_REPROCESS_QUEUED",
            entity_type="document",
            entity_id=doc.id,
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(doc)

    ingest_document_task.delay(str(doc.id), True)

    chunk_count = db.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc.id)
    ) or 0
    return _to_document_out(doc, int(chunk_count))


@router.post("/{document_id}/index-vectors")
def index_document_vectors(
    document_id: uuid.UUID,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    from app.services.ai.exceptions import AIConfigurationError, AIProviderError
    from app.services.rag.retriever import index_document_chunks

    doc = db.scalar(select(Document).where(Document.id == document_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    try:
        indexed_count = index_document_chunks(
            db,
            doc,
            usable_for_generation=is_document_usable_for_generation(doc),
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="DOCUMENT_VECTORS_INDEXED",
            entity_type="document",
            entity_id=doc.id,
            after_state={"indexed_chunks": indexed_count},
        )
    )
    db.commit()
    return {"document_id": str(doc.id), "indexed_chunks": indexed_count}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> None:
    doc = db.scalar(select(Document).where(Document.id == document_id))
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    try:
        from app.services.rag.vector_store import QdrantVectorStore

        QdrantVectorStore().delete_document_vectors(doc.id)
    except Exception:
        pass

    file_path = Path(doc.storage_path)
    if file_path.exists() and file_path.is_file():
        file_path.unlink(missing_ok=True)

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="DOCUMENT_DELETED",
            entity_type="document",
            entity_id=doc.id,
            before_state={"title": doc.title, "sha256": doc.sha256_hash},
            ip_address=request.client.host if request.client else None,
        )
    )
    db.delete(doc)
    db.commit()
