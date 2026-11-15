from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

SourceType = Literal["SYLLABUS", "PREVIOUS_BCS", "TEXTBOOK", "NOTES"]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    uploaded_by: uuid.UUID
    subject_id: uuid.UUID
    chapter_id: uuid.UUID | None
    title: str
    source_type: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    extraction_method: str
    legacy_encoding_detected: bool
    extraction_quality_score: float | None
    admin_confirmed_low_quality: bool
    usable_for_generation: bool
    page_count: int | None
    ingestion_status: str
    error_message: str | None
    chunk_count: int = 0
    created_at: datetime


class DocumentChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    page_number: int
    heading_path: str | None
    content_nfc: str
    token_count: int
    extraction_confidence: float | None
    created_at: datetime


class DocumentDetailOut(DocumentOut):
    chunks: list[DocumentChunkOut]


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int
