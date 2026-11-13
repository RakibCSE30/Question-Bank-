from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth import UserOut


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["ADMIN", "REVIEWER", "STUDENT"]
    preferred_lang: Literal["bn", "en"] = "bn"


class AdminUpdateUserRequest(BaseModel):
    role: Literal["ADMIN", "REVIEWER", "STUDENT"] | None = None
    is_active: bool | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    preferred_lang: Literal["bn", "en"] | None = None


class UserListResponse(BaseModel):
    items: list[UserOut]
    total: int


class DashboardMetricCard(BaseModel):
    key: str
    value: int | float | str


class DashboardSummaryResponse(BaseModel):
    role: Literal["ADMIN", "REVIEWER", "STUDENT"]
    phase: str = "phase_1_foundation"
    metrics: list[DashboardMetricCard]
    notices: list[str]
