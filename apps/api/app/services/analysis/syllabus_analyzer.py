from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.curriculum import SyllabusItem
from app.db.models.documents import Document, DocumentChunk
from app.db.models.logs import AIGenerationLog
from app.services.ai.base import LLMProvider
from app.services.ai.registry import get_llm_provider


class ExtractedSyllabusTopic(BaseModel):
    topic_bn: str = Field(min_length=2, max_length=500)
    topic_en: str | None = Field(default=None, max_length=500)
    weight_percentage: float = Field(ge=0.0, le=100.0)
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    priority_reason: str = Field(min_length=3)
    source_reference: str = Field(min_length=2)


class SyllabusExtractionOutput(BaseModel):
    items: list[ExtractedSyllabusTopic]


_SYSTEM_PROMPT = (
    "You are an expert Bangladesh BCS curriculum analyst. "
    "Extract structured syllabus topics ONLY from the provided document chunks. "
    "Do NOT invent topics, marks, or page numbers not present in the chunks. "
    "Assign priority (HIGH, MEDIUM, LOW) with a concise reason grounded in the text, "
    "and cite the page number / heading in source_reference."
)


def analyze_syllabus_document(
    db: Session,
    *,
    document: Document,
    triggered_by: uuid.UUID,
    llm_provider: LLMProvider | None = None,
) -> list[SyllabusItem]:
    settings = get_settings()
    chunks = list(
        db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .limit(40)
        ).all()
    )
    if not chunks:
        raise ValueError("Document has no extracted chunks to analyze.")

    context_blocks = [
        f"[Page {c.page_number} | Heading: {c.heading_path or 'N/A'} | ChunkID: {c.id}]\n{c.content_nfc}"
        for c in chunks
    ]
    user_prompt = (
        f"Analyze this syllabus document '{document.title}' and extract normalized syllabus items:\n\n"
        + "\n\n---\n\n".join(context_blocks)
    )

    provider = llm_provider or get_llm_provider()
    try:
        parsed, meta = provider.generate_structured(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=SyllabusExtractionOutput,
            model_name=settings.GENERATION_MODEL,
            temperature=0.2,
        )
    except Exception as exc:
        db.add(
            AIGenerationLog(
                stage="CONTENT_ANALYSIS",
                provider=settings.LLM_PROVIDER,
                model_name=settings.GENERATION_MODEL,
                prompt_version="syllabus-v1",
                status="PROVIDER_ERROR",
                error_detail=str(exc),
                triggered_by=triggered_by,
            )
        )
        db.commit()
        raise

    db.add(
        AIGenerationLog(
            stage="CONTENT_ANALYSIS",
            provider=meta.provider,
            model_name=meta.model_name,
            prompt_version="syllabus-v1",
            input_tokens=meta.input_tokens,
            output_tokens=meta.output_tokens,
            latency_ms=meta.latency_ms,
            status="SUCCESS",
            triggered_by=triggered_by,
        )
    )

    created_items: list[SyllabusItem] = []
    for item in parsed.items:
        row = SyllabusItem(
            subject_id=document.subject_id,
            chapter_id=document.chapter_id,
            topic_bn=item.topic_bn.strip(),
            topic_en=item.topic_en.strip() if item.topic_en else None,
            weight_percentage=Decimal(f"{item.weight_percentage:.2f}"),
            priority=item.priority,
            priority_reason=item.priority_reason.strip(),
            source_reference=item.source_reference.strip(),
        )
        db.add(row)
        created_items.append(row)

    db.commit()
    for row in created_items:
        db.refresh(row)
    return created_items
