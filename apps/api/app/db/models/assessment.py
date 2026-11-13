from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, DateTimeUTC, JSONBType, utc_now


class PracticeSet(Base):
    __tablename__ = "practice_sets"
    __table_args__ = (
        CheckConstraint("negative_mark_per_wrong >= 0", name="ck_practice_sets_nonneg_penalty"),
        CheckConstraint("marks_per_correct > 0", name="ck_practice_sets_pos_marks"),
        CheckConstraint("duration_minutes > 0", name="ck_practice_sets_pos_duration"),
        Index("ix_practice_sets_subject_published", "subject_id", "is_published"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title_bn: Mapped[str] = mapped_column(String(255), nullable=False)
    target_question_count: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    # Admin-configurable: never assumed by default
    negative_mark_per_wrong: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.00"), nullable=False)
    marks_per_correct: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("1.00"), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    items: Mapped[list["PracticeSetQuestion"]] = relationship(
        back_populates="practice_set", cascade="all, delete-orphan"
    )


class PracticeSetQuestion(Base):
    __tablename__ = "practice_set_questions"
    __table_args__ = (
        UniqueConstraint("practice_set_id", "question_id", name="uq_practice_set_q_unique"),
        UniqueConstraint("practice_set_id", "position", name="uq_practice_set_q_pos"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    practice_set_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("practice_sets.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("generated_questions.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    practice_set: Mapped[PracticeSet] = relationship(back_populates="items")


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    __table_args__ = (
        CheckConstraint("status IN ('IN_PROGRESS', 'SUBMITTED', 'TIMED_OUT')", name="ck_test_attempts_status"),
        Index("ix_test_attempts_student_started", "student_id", "started_at"),
        Index("ix_test_attempts_practice_set", "practice_set_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    practice_set_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("practice_sets.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="IN_PROGRESS", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTimeUTC, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    negative_deduction: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    final_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    responses: Mapped[list["StudentResponse"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class StudentResponse(Base):
    __tablename__ = "student_responses"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_student_resp_attempt_q"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("generated_questions.id", ondelete="RESTRICT"), nullable=False
    )
    selected_option_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("question_options.id", ondelete="SET NULL"), nullable=True
    )
    is_marked_for_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTimeUTC, nullable=True)

    attempt: Mapped[TestAttempt] = relationship(back_populates="responses")


class PerformanceReport(Base):
    __tablename__ = "performance_reports"
    __table_args__ = (
        Index("ix_perf_reports_student_created", "student_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("test_attempts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    accuracy_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    topic_breakdown_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    difficulty_breakdown_json: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    weak_topics_json: Mapped[list | dict] = mapped_column(JSONBType, nullable=False)
    revision_recommendations_bn: Mapped[list | dict] = mapped_column(JSONBType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
