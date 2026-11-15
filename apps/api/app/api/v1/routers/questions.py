from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import get_current_user, require_roles
from app.db.models.assessment import PracticeSet, PracticeSetQuestion
from app.db.models.curriculum import Subject
from app.db.models.questions import GeneratedQuestion
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.questions import (
    GeneratePilotSetsRequest,
    GeneratedQuestionOut,
    PracticeSetDetailOut,
    PracticeSetOut,
    PublishSetRequest,
    QuestionReviewUpdate,
)
from app.services.generator.mcq_generator import generate_bangla_literature_pilot_sets

router = APIRouter(prefix="/questions", tags=["Question Bank & Generation"])


@router.post(
    "/generate-pilot-sets",
    response_model=list[PracticeSetOut],
    status_code=status.HTTP_201_CREATED,
)
def generate_pilot_sets(
    payload: GeneratePilotSetsRequest = GeneratePilotSetsRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> list[PracticeSetOut]:
    """Admin endpoint to generate or instantiate the 5 pilot practice sets (75 MCQs) for Bangla Literature."""
    try:
        sets = generate_bangla_literature_pilot_sets(
            db,
            triggered_by=current_user.id,
            num_sets=payload.num_sets,
            questions_per_set=payload.questions_per_set,
        )

        results: list[PracticeSetOut] = []
        for s in sets:
            count = db.scalar(
                select(func.count(PracticeSetQuestion.id)).where(PracticeSetQuestion.practice_set_id == s.id)
            ) or 0
            out = PracticeSetOut.model_validate(s)
            out.question_count = count
            results.append(out)

        return results
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"পাইলট প্রশ্ন সেট তৈরি করতে ত্রুটি হয়েছে: {str(exc)}",
        ) from exc


@router.get(
    "/practice-sets",
    response_model=list[PracticeSetOut],
    status_code=status.HTTP_200_OK,
)
def list_practice_sets(
    subject_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PracticeSetOut]:
    """List practice sets. Students only see published sets; Admin and Reviewer see all."""
    query = select(PracticeSet)

    if subject_code:
        subj = db.scalar(select(Subject).where(Subject.code == subject_code))
        if subj:
            query = query.where(PracticeSet.subject_id == subj.id)

    # Students can only access published sets
    if current_user.role.name == "STUDENT":
        query = query.where(PracticeSet.is_published.is_(True))

    sets = list(db.scalars(query.order_by(PracticeSet.set_number.asc())).all())

    results: list[PracticeSetOut] = []
    for s in sets:
        count = db.scalar(
            select(func.count(PracticeSetQuestion.id)).where(PracticeSetQuestion.practice_set_id == s.id)
        ) or 0
        out = PracticeSetOut.model_validate(s)
        out.question_count = count
        results.append(out)

    return results


@router.get(
    "/practice-sets/{set_id}",
    response_model=PracticeSetDetailOut,
    status_code=status.HTTP_200_OK,
)
def get_practice_set_detail(
    set_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeSetDetailOut:
    """Get full details of a practice set including its questions and options."""
    practice_set = db.scalar(
        select(PracticeSet)
        .options(
            joinedload(PracticeSet.items)
            .joinedload(PracticeSetQuestion.question)
            .joinedload(GeneratedQuestion.options),
            joinedload(PracticeSet.items)
            .joinedload(PracticeSetQuestion.question)
            .joinedload(GeneratedQuestion.answer_key),
        )
        .where(PracticeSet.id == set_id)
    )

    if not practice_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="প্র্যাকটিস সেট পাওয়া যায়নি।",
        )

    if current_user.role.name == "STUDENT" and not practice_set.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="এই প্র্যাকটিস সেটটি এখনও শিক্ষার্থীদের জন্য উন্মুক্ত করা হয়নি।",
        )

    # Sort items by position
    practice_set.items.sort(key=lambda x: x.position)

    out = PracticeSetDetailOut.model_validate(practice_set)
    out.question_count = len(practice_set.items)
    return out


@router.get(
    "/{question_id}",
    response_model=GeneratedQuestionOut,
    status_code=status.HTTP_200_OK,
)
def get_question_detail(
    question_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("ADMIN", "REVIEWER")),
) -> GeneratedQuestionOut:
    """Get single question details with options and answer key."""
    question = db.scalar(
        select(GeneratedQuestion)
        .options(
            joinedload(GeneratedQuestion.options),
            joinedload(GeneratedQuestion.answer_key),
        )
        .where(GeneratedQuestion.id == question_id)
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="প্রশ্নটি পাওয়া যায়নি।",
        )
    return GeneratedQuestionOut.model_validate(question)


@router.patch(
    "/{question_id}/review",
    response_model=GeneratedQuestionOut,
    status_code=status.HTTP_200_OK,
)
def review_question(
    question_id: uuid.UUID,
    payload: QuestionReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "REVIEWER")),
) -> GeneratedQuestionOut:
    """Human Reviewer/Admin approves, rejects, or marks question for review."""
    question = db.scalar(
        select(GeneratedQuestion)
        .options(
            joinedload(GeneratedQuestion.options),
            joinedload(GeneratedQuestion.answer_key),
        )
        .where(GeneratedQuestion.id == question_id)
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="প্রশ্নটি পাওয়া যায়নি।",
        )

    question.status = payload.status
    question.reviewed_by = current_user.id
    db.commit()
    db.refresh(question)

    return GeneratedQuestionOut.model_validate(question)


@router.patch(
    "/practice-sets/{set_id}/publish",
    response_model=PracticeSetOut,
    status_code=status.HTTP_200_OK,
)
def publish_practice_set(
    set_id: uuid.UUID,
    payload: PublishSetRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("ADMIN")),
) -> PracticeSetOut:
    """Admin publishes or unpublishes a practice set, with optional negative marking configuration."""
    practice_set = db.scalar(select(PracticeSet).where(PracticeSet.id == set_id))
    if not practice_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="প্র্যাকটিস সেটটি পাওয়া যায়নি।",
        )

    practice_set.is_published = payload.is_published
    if payload.negative_mark_per_wrong is not None:
        practice_set.negative_mark_per_wrong = payload.negative_mark_per_wrong
    if payload.duration_minutes is not None:
        practice_set.duration_minutes = payload.duration_minutes

    db.commit()
    db.refresh(practice_set)

    count = db.scalar(
        select(func.count(PracticeSetQuestion.id)).where(PracticeSetQuestion.practice_set_id == practice_set.id)
    ) or 0
    out = PracticeSetOut.model_validate(practice_set)
    out.question_count = count
    return out
