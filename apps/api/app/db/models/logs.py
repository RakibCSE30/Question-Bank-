from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import GUID, Base, DateTimeUTC, JSONBType, utc_now


class AIGenerationLog(Base):
    __tablename__ = "ai_generation_logs"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('INGEST_EXTRACT', 'CONTENT_ANALYSIS', 'MCQ_GEN', 'VERIFICATION', 'WRITTEN_GEN', 'WRITTEN_EVAL')",
            name="ck_ai_logs_stage",
        ),
        CheckConstraint("status IN ('SUCCESS', 'VALIDATION_ERROR', 'PROVIDER_ERROR')", name="ck_ai_logs_status"),
        Index("ix_ai_logs_stage_created", "stage", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
