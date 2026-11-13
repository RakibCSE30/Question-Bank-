from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, DateTimeUTC, utc_now


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_bn: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    bcs_total_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    chapters: Mapped[list["Chapter"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (
        UniqueConstraint("subject_id", "order_index", name="uq_chapters_subject_order"),
        Index("ix_chapters_subject_id", "subject_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title_bn: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    subject: Mapped[Subject] = relationship(back_populates="chapters")


class SyllabusItem(Base):
    __tablename__ = "syllabus_items"
    __table_args__ = (
        CheckConstraint("priority IN ('HIGH', 'MEDIUM', 'LOW')", name="ck_syllabus_priority"),
        CheckConstraint("weight_percentage >= 0 AND weight_percentage <= 100", name="ck_syllabus_weight"),
        Index("ix_syllabus_subject_chapter_priority", "subject_id", "chapter_id", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    subject_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    topic_bn: Mapped[str] = mapped_column(String(500), nullable=False)
    topic_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    weight_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="MEDIUM", nullable=False)
    priority_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
