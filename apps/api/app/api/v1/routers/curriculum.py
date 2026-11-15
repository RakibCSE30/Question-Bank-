from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_roles
from app.db.models.curriculum import Chapter, Subject
from app.db.models.logs import AuditLog
from app.db.models.users import User
from app.db.seed import seed_bangla_literature
from app.db.session import get_db
from app.schemas.curriculum import (
    ChapterCreate,
    ChapterOut,
    ChapterUpdate,
    SubjectCreate,
    SubjectOut,
    SubjectUpdate,
)

router = APIRouter(tags=["curriculum"])


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.created_at.asc())).all())


@router.post("/admin/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate,
    request: Request,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Subject:
    code = payload.code.strip().upper()
    if db.scalar(select(Subject).where(Subject.code == code)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subject code already exists.")

    subject = Subject(
        code=code,
        name_bn=payload.name_bn.strip(),
        name_en=payload.name_en.strip(),
        bcs_total_marks=payload.bcs_total_marks,
    )
    db.add(subject)
    db.flush()

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="SUBJECT_CREATED",
            entity_type="subject",
            entity_id=subject.id,
            after_state={"code": subject.code, "name_bn": subject.name_bn},
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(subject)
    return subject


@router.post("/admin/subjects/seed-pilot", response_model=SubjectOut)
def seed_pilot_subject(
    request: Request,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Subject:
    subject, created = seed_bangla_literature(db)
    if created:
        db.add(
            AuditLog(
                actor_id=admin.id,
                actor_role=admin.role.name,
                action="PILOT_SUBJECT_SEEDED",
                entity_type="subject",
                entity_id=subject.id,
                after_state={"code": subject.code, "name_bn": subject.name_bn},
                ip_address=request.client.host if request.client else None,
            )
        )
        db.commit()
    return subject


@router.patch("/admin/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdate,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Subject:
    subject = db.scalar(select(Subject).where(Subject.id == subject_id))
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    if payload.name_bn is not None:
        subject.name_bn = payload.name_bn.strip()
    if payload.name_en is not None:
        subject.name_en = payload.name_en.strip()
    if payload.bcs_total_marks is not None:
        subject.bcs_total_marks = payload.bcs_total_marks
    if payload.is_active is not None:
        subject.is_active = payload.is_active

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="SUBJECT_UPDATED",
            entity_type="subject",
            entity_id=subject.id,
        )
    )
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/admin/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: uuid.UUID,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> None:
    subject = db.scalar(select(Subject).where(Subject.id == subject_id))
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")
    db.delete(subject)
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="SUBJECT_DELETED",
            entity_type="subject",
            entity_id=subject_id,
        )
    )
    db.commit()


@router.get("/subjects/{subject_id}/chapters", response_model=list[ChapterOut])
def list_chapters(
    subject_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Chapter]:
    return list(
        db.scalars(
            select(Chapter)
            .where(Chapter.subject_id == subject_id)
            .order_by(Chapter.order_index.asc())
        ).all()
    )


@router.post(
    "/admin/subjects/{subject_id}/chapters",
    response_model=ChapterOut,
    status_code=status.HTTP_201_CREATED,
)
def create_chapter(
    subject_id: uuid.UUID,
    payload: ChapterCreate,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Chapter:
    subject = db.scalar(select(Subject).where(Subject.id == subject_id))
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    dup = db.scalar(
        select(Chapter).where(
            Chapter.subject_id == subject_id,
            Chapter.order_index == payload.order_index,
        )
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A chapter with this order_index already exists for the subject.",
        )

    chapter = Chapter(
        subject_id=subject_id,
        order_index=payload.order_index,
        title_bn=payload.title_bn.strip(),
        title_en=payload.title_en.strip() if payload.title_en else None,
    )
    db.add(chapter)
    db.flush()
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="CHAPTER_CREATED",
            entity_type="chapter",
            entity_id=chapter.id,
            after_state={"subject_id": str(subject_id), "title_bn": chapter.title_bn},
        )
    )
    db.commit()
    db.refresh(chapter)
    return chapter


@router.patch("/admin/chapters/{chapter_id}", response_model=ChapterOut)
def update_chapter(
    chapter_id: uuid.UUID,
    payload: ChapterUpdate,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Chapter:
    chapter = db.scalar(select(Chapter).where(Chapter.id == chapter_id))
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")

    if payload.order_index is not None:
        chapter.order_index = payload.order_index
    if payload.title_bn is not None:
        chapter.title_bn = payload.title_bn.strip()
    if payload.title_en is not None:
        chapter.title_en = payload.title_en.strip()

    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="CHAPTER_UPDATED",
            entity_type="chapter",
            entity_id=chapter.id,
        )
    )
    db.commit()
    db.refresh(chapter)
    return chapter


@router.delete("/admin/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(
    chapter_id: uuid.UUID,
    admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> None:
    chapter = db.scalar(select(Chapter).where(Chapter.id == chapter_id))
    if chapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found.")
    db.delete(chapter)
    db.add(
        AuditLog(
            actor_id=admin.id,
            actor_role=admin.role.name,
            action="CHAPTER_DELETED",
            entity_type="chapter",
            entity_id=chapter_id,
        )
    )
    db.commit()
