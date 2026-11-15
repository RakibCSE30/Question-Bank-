from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class QuestionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    option_label: Literal["ক", "খ", "গ", "ঘ"]
    option_text_bn: str
    sort_order: int


class AnswerKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    correct_option_id: uuid.UUID
    correct_label: Literal["ক", "খ", "গ", "ঘ"]
    rationale_bn: str | None


class GeneratedQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    chapter_id: uuid.UUID | None
    batch_job_id: uuid.UUID
    question_text_bn: str
    explanation_bn: str
    question_style: str
    difficulty: Literal["EASY", "MEDIUM", "HARD"]
    importance: Literal["HIGH", "MEDIUM", "LOW"]
    grounding_type: Literal["SOURCE_GROUNDED", "AI_INFERENCE"]
    source_citations_json: list[dict[str, Any]] | dict[str, Any]
    previous_bcs_relation: Literal["EXACT_REPEAT", "SIMILAR_TOPIC", "NONE"]
    status: Literal["GENERATED", "VERIFIED", "NEEDS_REVIEW", "REJECTED", "APPROVED"]
    options: list[QuestionOptionOut] = []
    answer_key: AnswerKeyOut | None = None
    created_at: datetime


class PracticeSetQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    question: GeneratedQuestionOut


class PracticeSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    chapter_id: uuid.UUID | None
    set_number: int
    title_bn: str
    target_question_count: int
    duration_minutes: int
    negative_mark_per_wrong: Decimal
    marks_per_correct: Decimal
    is_published: bool
    created_at: datetime
    question_count: int = 0


class PracticeSetDetailOut(PracticeSetOut):
    items: list[PracticeSetQuestionOut] = []


class GeneratePilotSetsRequest(BaseModel):
    subject_code: str = Field(default="BANGLA_LIT")
    num_sets: int = Field(default=5, ge=1, le=10)
    questions_per_set: int = Field(default=15, ge=5, le=50)


class QuestionReviewUpdate(BaseModel):
    status: Literal["APPROVED", "REJECTED", "NEEDS_REVIEW"]
    review_notes: str | None = None


class PublishSetRequest(BaseModel):
    is_published: bool
    negative_mark_per_wrong: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("2.00"))
    duration_minutes: int | None = Field(default=None, ge=5, le=120)
