from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base, DateTimeUTC, JSONBType, UUIDArrayType, utc_now


class WrittenQuestion(Base):
    __tablename__ = "written_questions"
    __table_args__ = (
        CheckConstraint("max_marks > 0", name="ck_written_q_pos_marks"),
        CheckConstraint("grounding_type IN ('SOURCE_GROUNDED', 'AI_INFERENCE')", name="ck_written_q_grounding"),
        CheckConstraint(
            "status IN ('GENERATED', 'VERIFIED', 'NEEDS_REVIEW', 'REJECTED', 'APPROVED')",
            name="ck_written_q_status",
        ),
        Index("ix_written_questions_subj_status", "subject_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    syllabus_item_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("syllabus_items.id", ondelete="SET NULL"), nullable=True
    )
    prompt_bn: Mapped[str] = mapped_column(Text, nullable=False)
    max_marks: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    model_answer_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    rubric_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    source_chunk_ids: Mapped[list[uuid.UUID]] = mapped_column(UUIDArrayType, nullable=False)
    grounding_type: Mapped[str] = mapped_column(String(24), default="SOURCE_GROUNDED", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="GENERATED", nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)


class WrittenAnswer(Base):
    __tablename__ = "written_answers"
    __table_args__ = (
        Index("ix_written_answers_student_created", "student_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    written_question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("written_questions.id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    answer_text_bn: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    rubric_scores_json: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    feedback_bn: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    disclaimer_label: Mapped[str] = mapped_column(
        String(255),
        default="Educational estimate, not an official examiner score",
        nullable=False,
    )
    ai_log_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("ai_generation_logs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
