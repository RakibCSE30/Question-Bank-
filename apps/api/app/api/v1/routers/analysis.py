from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, require_roles
from app.db.models.curriculum import Subject
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.analysis import BanglaLiteratureAnalysisReport, PreviousQuestionsTrendAnalysis
from app.services.analysis.bangla_literature import (
    analyze_bangla_literature_topics_and_previous_trends,
    seed_bangla_literature_baseline,
)

router = APIRouter(prefix="/analysis", tags=["Curriculum Analysis & Entities"])


@router.post(
    "/bangla-literature/seed-baseline",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
def seed_bangla_baseline(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("ADMIN")),
) -> dict[str, Any]:
    """Seed standard 5 chapters, core syllabus items, and authentic previous questions for Bangla Literature."""
    result = seed_bangla_literature_baseline(db)
    return {
        "status": "success",
        "message": "বাংলা সাহিত্যের ৫টি অধ্যায়, সিলেবাস আইটেম এবং বিগত বিসিএস প্রশ্ন সফলভাবে সংরক্ষিত হয়েছে।",
        "data": result,
    }


@router.get(
    "/bangla-literature/report",
    response_model=BanglaLiteratureAnalysisReport,
    status_code=status.HTTP_200_OK,
)
def get_bangla_literature_report(
    db: Session = Depends(get_db),
    subject_id: uuid.UUID | None = Query(default=None),
    _user: User = Depends(require_roles("ADMIN", "REVIEWER")),
) -> BanglaLiteratureAnalysisReport:
    """Get comprehensive entity map, literary periods, topic priorities, and previous BCS trends."""
    if subject_id is None:
        subj = db.scalar(select(Subject).where(Subject.code == "BANGLA_LIT"))
        if not subj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="বাংলা সাহিত্য বিষয় এখনও তৈরি করা হয়নি। অনুগ্রহ করে প্রথমে বেসলাইন সীড করুন।",
            )
        subject_id = subj.id

    try:
        return analyze_bangla_literature_topics_and_previous_trends(db, subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/bangla-literature/previous-trends",
    response_model=PreviousQuestionsTrendAnalysis,
    status_code=status.HTTP_200_OK,
)
def get_previous_trends(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("ADMIN", "REVIEWER")),
) -> PreviousQuestionsTrendAnalysis:
    """Analyze question patterns, styles, and frequencies across past BCS exams."""
    subj = db.scalar(select(Subject).where(Subject.code == "BANGLA_LIT"))
    if not subj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="বাংলা সাহিত্য বিষয় এখনও তৈরি করা হয়নি।",
        )
    report = analyze_bangla_literature_topics_and_previous_trends(db, subj.id)
    return report.previous_trends
