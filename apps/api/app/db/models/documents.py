from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, DateTimeUTC, utc_now


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('SYLLABUS', 'PREVIOUS_BCS', 'TEXTBOOK', 'NOTES')",
            name="ck_documents_source_type",
        ),
        CheckConstraint(
            "extraction_method IN ('PYMUPDF', 'DOCX', 'OCR_TESSERACT', 'TXT', 'IMAGE_OCR')",
            name="ck_documents_extraction_method",
        ),
        CheckConstraint(
            "ingestion_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FLAGGED', 'FAILED')",
            name="ck_documents_ingestion_status",
        ),
        Index("ix_documents_subject_chapter_status", "subject_id", "chapter_id", "ingestion_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(32), default="PYMUPDF", nullable=False)
    legacy_encoding_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extraction_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    admin_confirmed_low_quality: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingestion_status: Mapped[str] = mapped_column(String(24), default="PENDING", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunks_doc_index"),
        Index("ix_doc_chunks_subject_chapter_page", "subject_id", "chapter_id", "page_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_nfc: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vector_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")
