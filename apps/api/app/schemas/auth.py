from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    preferred_lang: Literal["bn", "en"] = "bn"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    preferred_lang: Literal["bn", "en"]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_orm_user(cls, user: object) -> "UserOut":
        # Avoid circular imports; expects SQLAlchemy User with loaded .role
        return cls(
            id=getattr(user, "id"),
            email=getattr(user, "email"),
            full_name=getattr(user, "full_name"),
            role=getattr(getattr(user, "role"), "name"),
            preferred_lang=getattr(user, "preferred_lang"),
            is_active=getattr(user, "is_active"),
            created_at=getattr(user, "created_at"),
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
