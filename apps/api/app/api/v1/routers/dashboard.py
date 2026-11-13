from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.db.models.assessment import PracticeSet, TestAttempt
from app.db.models.curriculum import Subject
from app.db.models.documents import Document
from app.db.models.questions import GeneratedQuestion
from app.db.models.users import User
from app.db.session import get_db
from app.schemas.users import DashboardMetricCard, DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/student", response_model=DashboardSummaryResponse)
def student_dashboard(
    current_user: User = Depends(require_roles("STUDENT", "REVIEWER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    # Students only ever see published sets and APPROVED questions
    published_sets = db.scalar(
        select(func.count()).select_from(PracticeSet).where(PracticeSet.is_published.is_(True))
    ) or 0
    approved_questions = db.scalar(
        select(func.count()).select_from(GeneratedQuestion).where(GeneratedQuestion.status == "APPROVED")
    ) or 0
    my_attempts = db.scalar(
        select(func.count()).select_from(TestAttempt).where(TestAttempt.student_id == current_user.id)
    ) or 0
    active_subjects = db.scalar(
        select(func.count()).select_from(Subject).where(Subject.is_active.is_(True))
    ) or 0

    return DashboardSummaryResponse(
        role="STUDENT",
        metrics=[
            DashboardMetricCard(key="published_practice_sets", value=int(published_sets)),
            DashboardMetricCard(key="approved_questions", value=int(approved_questions)),
            DashboardMetricCard(key="my_attempts", value=int(my_attempts)),
            DashboardMetricCard(key="active_subjects", value=int(active_subjects)),
        ],
        notices=[
            "Only human-approved questions are displayed to students.",
        ],
    )


@router.get("/reviewer", response_model=DashboardSummaryResponse)
def reviewer_dashboard(
    _user: User = Depends(require_roles("REVIEWER", "ADMIN")),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    needs_review = db.scalar(
        select(func.count()).select_from(GeneratedQuestion).where(GeneratedQuestion.status == "NEEDS_REVIEW")
    ) or 0
    verified = db.scalar(
        select(func.count()).select_from(GeneratedQuestion).where(GeneratedQuestion.status == "VERIFIED")
    ) or 0
    approved = db.scalar(
        select(func.count()).select_from(GeneratedQuestion).where(GeneratedQuestion.status == "APPROVED")
    ) or 0
    rejected = db.scalar(
        select(func.count()).select_from(GeneratedQuestion).where(GeneratedQuestion.status == "REJECTED")
    ) or 0

    return DashboardSummaryResponse(
        role="REVIEWER",
        metrics=[
            DashboardMetricCard(key="needs_review_count", value=int(needs_review)),
            DashboardMetricCard(key="verified_pending_approval", value=int(verified)),
            DashboardMetricCard(key="approved_count", value=int(approved)),
            DashboardMetricCard(key="rejected_count", value=int(rejected)),
        ],
        notices=[
            "Verify every source citation and option distinctiveness before approving.",
        ],
    )


@router.get("/admin", response_model=DashboardSummaryResponse)
def admin_dashboard(
    _admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    total_documents = db.scalar(select(func.count()).select_from(Document)) or 0
    flagged_documents = db.scalar(
        select(func.count()).select_from(Document).where(Document.ingestion_status == "FLAGGED")
    ) or 0
    approved_questions = db.scalar(
        select(func.count()).select_from(GeneratedQuestion).where(GeneratedQuestion.status == "APPROVED")
    ) or 0

    return DashboardSummaryResponse(
        role="ADMIN",
        metrics=[
            DashboardMetricCard(key="total_users", value=int(total_users)),
            DashboardMetricCard(key="total_documents", value=int(total_documents)),
            DashboardMetricCard(key="flagged_documents", value=int(flagged_documents)),
            DashboardMetricCard(key="approved_questions", value=int(approved_questions)),
        ],
        notices=[
            "Phase 1 foundation active. Study material ingestion starts in Phase 2.",
        ],
    )
