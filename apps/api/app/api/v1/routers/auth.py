from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_refresh_token_hash,
)
from app.db.models.logs import AuditLog
from app.db.models.users import Role, User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _record_audit(
    db: Session,
    *,
    actor_id: uuid.UUID | None,
    actor_role: str | None,
    action: str,
    entity_id: uuid.UUID | None,
    ip_address: str | None,
    after_state: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type="user",
            entity_id=entity_id,
            after_state=after_state,
            ip_address=ip_address,
        )
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    student_role = db.scalar(select(Role).where(Role.name == "STUDENT"))
    if student_role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System roles are not initialized.",
        )

    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role_id=student_role.id,
        preferred_lang=payload.preferred_lang,
        is_active=True,
    )
    db.add(user)
    db.flush()

    access_token, expires_in = create_access_token(user_id=user.id, role="STUDENT")
    refresh_token = create_refresh_token(user_id=user.id, role="STUDENT")
    user.refresh_token_hash = hash_refresh_token(refresh_token)
    user.role = student_role

    _record_audit(
        db,
        actor_id=user.id,
        actor_role="STUDENT",
        action="USER_REGISTERED",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
        after_state={"email": user.email, "role": "STUDENT"},
    )
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserOut.from_orm_user(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    normalized_email = payload.email.strip().lower()
    user = db.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(User.email == normalized_email)
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    role_name = user.role.name
    access_token, expires_in = create_access_token(user_id=user.id, role=role_name)
    refresh_token = create_refresh_token(user_id=user.id, role=role_name)
    user.refresh_token_hash = hash_refresh_token(refresh_token)

    _record_audit(
        db,
        actor_id=user.id,
        actor_role=role_name,
        action="USER_LOGIN",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserOut.from_orm_user(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        decoded = decode_refresh_token(payload.refresh_token)
        user_id = uuid.UUID(str(decoded["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user = db.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(User.id == user_id)
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or unavailable.",
        )

    if not verify_refresh_token_hash(payload.refresh_token, user.refresh_token_hash):
        # Revoke active refresh session if token reuse / mismatch occurs
        user.refresh_token_hash = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or rotated.",
        )

    role_name = user.role.name
    new_access_token, expires_in = create_access_token(user_id=user.id, role=role_name)
    new_refresh_token = create_refresh_token(user_id=user.id, role=role_name)
    user.refresh_token_hash = hash_refresh_token(new_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
        user=UserOut.from_orm_user(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    _payload: LogoutRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    current_user.refresh_token_hash = None
    db.commit()


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_orm_user(current_user)
