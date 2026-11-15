from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.documents import Document, DocumentChunk
from app.db.session import SessionLocal
from app.services.ingestion.chunker import chunk_pages
from app.services.ingestion.pdf_extractor import extract_document
from app.services.ingestion.validator import compute_text_similarity
from app.workers.celery_app import celery_app


def is_document_usable_for_generation(doc: Document) -> bool:
    """FLAGGED documents cannot be used for generation until Admin explicitly confirms them."""
    if doc.ingestion_status == "COMPLETED":
        return True
    if doc.ingestion_status == "FLAGGED" and doc.admin_confirmed_low_quality:
        return True
    return False


def process_document_ingestion(db: Session, document_id: uuid.UUID, *, force_ocr: bool = False) -> Document:
    settings = get_settings()
    doc = db.scalar(select(Document).where(Document.id == document_id))
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    doc.ingestion_status = "PROCESSING"
    doc.error_message = None
    db.commit()

    try:
        result = extract_document(doc.storage_path, force_ocr=force_ocr)
        chunks = chunk_pages(result.pages)

        # Replace existing chunks cleanly for idempotent OCR reprocessing
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

        for chunk in chunks:
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    subject_id=doc.subject_id,
                    chapter_id=doc.chapter_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    heading_path=chunk.heading_path,
                    content_nfc=chunk.content_nfc,
                    token_count=chunk.token_count,
                    extraction_confidence=Decimal(str(chunk.extraction_confidence)),
                )
            )

        # Near-duplicate detection against existing documents in the same subject
        full_doc_text = "\n".join(p.text for p in result.pages if p.text)
        near_dup_warning: str | None = None
        if full_doc_text:
            other_docs = db.scalars(
                select(Document).where(
                    Document.subject_id == doc.subject_id,
                    Document.id != doc.id,
                    Document.ingestion_status.in_(["COMPLETED", "FLAGGED"]),
                )
            ).all()
            for other in other_docs:
                other_chunks = db.scalars(
                    select(DocumentChunk.content_nfc)
                    .where(DocumentChunk.document_id == other.id)
                    .order_by(DocumentChunk.chunk_index.asc())
                    .limit(12)
                ).all()
                other_text = "\n".join(other_chunks)
                sim = compute_text_similarity(full_doc_text[:6000], other_text[:6000])
                if sim >= 0.85:
                    near_dup_warning = f"Near-duplicate content detected ({sim:.0%} similarity with '{other.title}')."
                    break

        doc.extraction_method = result.extraction_method
        doc.legacy_encoding_detected = result.legacy_encoding_detected
        doc.extraction_quality_score = Decimal(str(result.extraction_quality_score))
        doc.page_count = result.page_count

        if result.extraction_quality_score < settings.OCR_QUALITY_THRESHOLD:
            doc.ingestion_status = "FLAGGED"
            doc.admin_confirmed_low_quality = False
            msg = (
                f"Extraction quality score {result.extraction_quality_score:.3f} is below "
                f"threshold {settings.OCR_QUALITY_THRESHOLD:.2f}. Admin confirmation required."
            )
            doc.error_message = f"{msg} {near_dup_warning}".strip() if near_dup_warning else msg
        else:
            doc.ingestion_status = "COMPLETED"
            doc.error_message = near_dup_warning

        db.commit()
        db.refresh(doc)

        # Best-effort Qdrant vector indexing (non-fatal if OPENAI_API_KEY is not yet configured)
        try:
            from app.services.rag.retriever import index_document_chunks

            index_document_chunks(
                db,
                doc,
                usable_for_generation=is_document_usable_for_generation(doc),
            )
        except Exception as vec_exc:
            note = f"Vector indexing skipped ({type(vec_exc).__name__}: {vec_exc})."
            doc.error_message = f"{doc.error_message} {note}".strip() if doc.error_message else note
            db.commit()
            db.refresh(doc)

        return doc
    except Exception as exc:
        doc.ingestion_status = "FAILED"
        doc.error_message = str(exc)
        db.commit()
        db.refresh(doc)
        raise


@celery_app.task(name="sqb.ingestion.process_document")
def ingest_document_task(document_id: str, force_ocr: bool = False) -> dict[str, str]:
    with SessionLocal() as db:
        doc = process_document_ingestion(db, uuid.UUID(document_id), force_ocr=force_ocr)
        return {"document_id": str(doc.id), "status": doc.ingestion_status}


@celery_app.task(name="sqb.questions.generate_pilot_sets")
def generate_pilot_sets_task(triggered_by_user_id: str, num_sets: int = 5) -> dict[str, Any]:
    from app.services.generator.mcq_generator import generate_bangla_literature_pilot_sets

    with SessionLocal() as db:
        sets = generate_bangla_literature_pilot_sets(
            db,
            triggered_by=uuid.UUID(triggered_by_user_id),
            num_sets=num_sets,
        )
        return {"created_sets_count": len(sets), "status": "COMPLETED"}
