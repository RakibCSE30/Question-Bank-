from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, DateTimeUTC, utc_now


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("name IN ('ADMIN', 'REVIEWER', 'STUDENT')", name="ck_roles_valid_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("preferred_lang IN ('bn', 'en')", name="ck_users_preferred_lang"),
        Index("ix_users_role_id", "role_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_lang: Mapped[str] = mapped_column(String(8), default="bn", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTimeUTC, default=utc_now, onupdate=utc_now, nullable=False)

    role: Mapped[Role] = relationship(back_populates="users")
