from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# Portable types: native PostgreSQL types in prod/Docker, SQLite fallback for fast unit tests
GUID = PG_UUID(as_uuid=True).with_variant(Uuid(as_uuid=True), "sqlite")
JSONBType = PG_JSONB(astext_type=None).with_variant(JSON(), "sqlite")
DateTimeUTC = DateTime(timezone=True)


class UUIDArrayType(TypeDecorator[list[uuid.UUID]]):
    """Stores UUID[] on PostgreSQL and JSON list of UUID strings on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(PG_UUID(as_uuid=True)))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: list[uuid.UUID] | None, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return [v if isinstance(v, uuid.UUID) else uuid.UUID(str(v)) for v in value]
        return [str(v) for v in value]

    def process_result_value(self, value: Any, dialect: Any) -> list[uuid.UUID] | None:
        if value is None:
            return None
        return [v if isinstance(v, uuid.UUID) else uuid.UUID(str(v)) for v in value]
