from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubjectCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    name_bn: str = Field(min_length=2, max_length=255)
    name_en: str = Field(min_length=2, max_length=255)
    bcs_total_marks: int = Field(default=0, ge=0, le=200)


class SubjectUpdate(BaseModel):
    name_bn: str | None = Field(default=None, min_length=2, max_length=255)
    name_en: str | None = Field(default=None, min_length=2, max_length=255)
    bcs_total_marks: int | None = Field(default=None, ge=0, le=200)
    is_active: bool | None = None


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name_bn: str
    name_en: str
    bcs_total_marks: int
    is_active: bool
    created_at: datetime


class ChapterCreate(BaseModel):
    order_index: int = Field(ge=1, le=500)
    title_bn: str = Field(min_length=2, max_length=255)
    title_en: str | None = Field(default=None, max_length=255)


class ChapterUpdate(BaseModel):
    order_index: int | None = Field(default=None, ge=1, le=500)
    title_bn: str | None = Field(default=None, min_length=2, max_length=255)
    title_en: str | None = Field(default=None, max_length=255)


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    order_index: int
    title_bn: str
    title_en: str | None
    created_at: datetime
