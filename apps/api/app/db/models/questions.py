from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, DateTimeUTC, JSONBType, UUIDArrayType, utc_now


class PreviousQuestion(Base):
    __tablename__ = "previous_questions"
    __table_args__ = (
        CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="ck_prev_q_difficulty"),
        Index("ix_prev_questions_subject_batch", "subject_id", "bcs_batch"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    syllabus_item_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("syllabus_items.id", ondelete="SET NULL"), nullable=True
    )
    bcs_batch: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_text_bn: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    correct_option: Mapped[str] = mapped_column(String(8), nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), default="FACTUAL", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    extracted_authors_works: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vector_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)


class GeneratedQuestion(Base):
    __tablename__ = "generated_questions"
    __table_args__ = (
        CheckConstraint(
            "question_style IN ('FACTUAL', 'AUTHOR_WORK', 'CHRONOLOGY', 'CONCEPTUAL', "
            "'STATEMENT', 'COMPARATIVE', 'ANALYTICAL', 'TRICKY')",
            name="ck_gen_q_style",
        ),
        CheckConstraint("difficulty IN ('EASY', 'MEDIUM', 'HARD')", name="ck_gen_q_difficulty"),
        CheckConstraint("importance IN ('HIGH', 'MEDIUM', 'LOW')", name="ck_gen_q_importance"),
        CheckConstraint("grounding_type IN ('SOURCE_GROUNDED', 'AI_INFERENCE')", name="ck_gen_q_grounding"),
        CheckConstraint(
            "previous_bcs_relation IN ('EXACT_REPEAT', 'SIMILAR_TOPIC', 'NONE')",
            name="ck_gen_q_prev_bcs_rel",
        ),
        CheckConstraint(
            "status IN ('GENERATED', 'VERIFIED', 'NEEDS_REVIEW', 'REJECTED', 'APPROVED')",
            name="ck_gen_q_status",
        ),
        Index("ix_gen_questions_status_subj_chap", "status", "subject_id", "chapter_id"),
        Index("ix_gen_questions_batch_job", "batch_job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    syllabus_item_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("syllabus_items.id", ondelete="SET NULL"), nullable=True
    )
    batch_job_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False)
    question_text_bn: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_bn: Mapped[str] = mapped_column(Text, nullable=False)
    question_style: Mapped[str] = mapped_column(String(24), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    importance: Mapped[str] = mapped_column(String(16), nullable=False)
    grounding_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(UUIDArrayType, nullable=False)
    source_citations_json: Mapped[list | dict] = mapped_column(JSONBType, nullable=False)
    verified_previous_bcs_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("previous_questions.id", ondelete="SET NULL"), nullable=True
    )
    previous_bcs_relation: Mapped[str] = mapped_column(String(24), default="NONE", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="GENERATED", nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    vector_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now, nullable=False)

    options: Mapped[list["QuestionOption"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    answer_key: Mapped["AnswerKey | None"] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )
    verifications: Mapped[list["QuestionVerification"]] = relationship(
        back_populates="question",
        foreign_keys="QuestionVerification.question_id",
        cascade="all, delete-orphan",
    )


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_label", name="uq_question_options_label"),
        CheckConstraint("option_label IN ('ক', 'খ', 'গ', 'ঘ')", name="ck_option_label_bengali"),
        CheckConstraint("sort_order >= 1 AND sort_order <= 4", name="ck_option_sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("generated_questions.id", ondelete="CASCADE"), nullable=False
    )
    option_label: Mapped[str] = mapped_column(String(8), nullable=False)
    option_text_bn: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    question: Mapped[GeneratedQuestion] = relationship(back_populates="options")


class AnswerKey(Base):
    __tablename__ = "answer_keys"
    __table_args__ = (
        CheckConstraint("correct_label IN ('ক', 'খ', 'গ', 'ঘ')", name="ck_answer_key_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("generated_questions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    correct_option_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("question_options.id", ondelete="RESTRICT"), nullable=False
    )
    correct_label: Mapped[str] = mapped_column(String(8), nullable=False)
    rationale_bn: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped[GeneratedQuestion] = relationship(back_populates="answer_key")


class QuestionVerification(Base):
    __tablename__ = "question_verifications"
    __table_args__ = (
        CheckConstraint("verdict IN ('VERIFIED', 'NEEDS_REVIEW', 'REJECTED')", name="ck_q_verification_verdict"),
        Index("ix_question_verifications_q_verdict", "question_id", "verdict"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("generated_questions.id", ondelete="CASCADE"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    source_support_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    answer_correctness_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ambiguity_detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unsupported_claims: Mapped[list | dict | None] = mapped_column(JSONBType, nullable=True)
    semantic_duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("generated_questions.id", ondelete="SET NULL"), nullable=True
    )
    max_similarity_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    option_quality_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_conflict_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reasons_json: Mapped[list | dict] = mapped_column(JSONBType, nullable=False)
    verifier_model: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    question: Mapped[GeneratedQuestion] = relationship(
        back_populates="verifications",
        foreign_keys=[question_id],
    )
