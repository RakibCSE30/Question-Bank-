from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import require_roles
from app.core.security import hash_password
from app.db.models.logs import AuditLog
from app.db.models.users import Role, User
from app.db.session import get_db
from app.schemas.auth import UserOut
from app.schemas.users import AdminCreateUserRequest, AdminUpdateUserRequest, UserListResponse

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=UserListResponse)
def list_users(
    _admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserListResponse:
    users = db.scalars(
        select(User).options(joinedload(User.role)).order_by(User.created_at.desc())
    ).all()
    total = db.scalar(select(func.count()).select_from(User)) or 0
    return UserListResponse(
        items=[UserOut.from_orm_user(u) for u in users],
        total=int(total),
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUserRequest,
    request: Request,
    admin_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserOut:
    normalized_email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == normalized_email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    role = db.scalar(select(Role).where(Role.name == payload.role))
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")

    new_user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role_id=role.id,
        preferred_lang=payload.preferred_lang,
        is_active=True,
    )
    db.add(new_user)
    db.flush()
    new_user.role = role

    db.add(
        AuditLog(
            actor_id=admin_user.id,
            actor_role=admin_user.role.name,
            action="ADMIN_CREATED_USER",
            entity_type="user",
            entity_id=new_user.id,
            after_state={"email": new_user.email, "role": role.name},
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(new_user)
    return UserOut.from_orm_user(new_user)


@router.patch("/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: uuid.UUID,
    payload: AdminUpdateUserRequest,
    request: Request,
    admin_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> UserOut:
    target = db.scalar(select(User).options(joinedload(User.role)).where(User.id == user_id))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    before_state = {
        "role": target.role.name,
        "is_active": target.is_active,
        "full_name": target.full_name,
        "preferred_lang": target.preferred_lang,
    }

    if payload.role is not None:
        role = db.scalar(select(Role).where(Role.name == payload.role))
        if role is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")
        target.role_id = role.id
        target.role = role

    if payload.is_active is not None:
        if target.id == admin_user.id and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin cannot deactivate their own account.",
            )
        target.is_active = payload.is_active
        if not payload.is_active:
            target.refresh_token_hash = None

    if payload.full_name is not None:
        target.full_name = payload.full_name.strip()

    if payload.preferred_lang is not None:
        target.preferred_lang = payload.preferred_lang

    after_state = {
        "role": target.role.name,
        "is_active": target.is_active,
        "full_name": target.full_name,
        "preferred_lang": target.preferred_lang,
    }

    db.add(
        AuditLog(
            actor_id=admin_user.id,
            actor_role=admin_user.role.name,
            action="ADMIN_UPDATED_USER",
            entity_type="user",
            entity_id=target.id,
            before_state=before_state,
            after_state=after_state,
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(target)
    return UserOut.from_orm_user(target)
