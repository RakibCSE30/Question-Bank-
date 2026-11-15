from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.assessment import PracticeSet, PracticeSetQuestion
from app.db.models.curriculum import Chapter, Subject, SyllabusItem
from app.db.models.questions import AnswerKey, GeneratedQuestion, PreviousQuestion, QuestionOption
from tests.conftest import auth_headers_for, create_user_with_role


def test_phase4_seed_and_literature_analysis(client: TestClient, db_session: Session) -> None:
    admin = create_user_with_role(db_session, email="p4_admin@example.com", role_name="ADMIN")
    student = create_user_with_role(db_session, email="p4_student@example.com", role_name="STUDENT")

    admin_headers = auth_headers_for(admin)
    student_headers = auth_headers_for(student)

    # 1. Student is forbidden from seeding baseline
    resp_student = client.post("/api/v1/analysis/bangla-literature/seed-baseline", headers=student_headers)
    assert resp_student.status_code == 403

    # 2. Admin seeds baseline
    resp = client.post("/api/v1/analysis/bangla-literature/seed-baseline", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["subject_code"] == "BANGLA_LIT"

    # Verify chapters created
    subj = db_session.scalar(select(Subject).where(Subject.code == "BANGLA_LIT"))
    assert subj is not None
    chapters = list(db_session.scalars(select(Chapter).where(Chapter.subject_id == subj.id)).all())
    assert len(chapters) == 5

    # Verify syllabus items and previous questions seeded
    item_count = db_session.scalar(
        select(func.count(SyllabusItem.id)).where(SyllabusItem.subject_id == subj.id)
    )
    assert item_count >= 20

    prev_q_count = db_session.scalar(
        select(func.count(PreviousQuestion.id)).where(PreviousQuestion.subject_id == subj.id)
    )
    assert prev_q_count >= 6

    # 3. Fetch comprehensive report
    rep_resp = client.get("/api/v1/analysis/bangla-literature/report", headers=admin_headers)
    assert rep_resp.status_code == 200
    rep = rep_resp.json()
    assert rep["subject_code"] == "BANGLA_LIT"
    assert len(rep["periods"]) == 5
    assert len(rep["authors"]) >= 5
    assert len(rep["literary_works"]) >= 4
    assert len(rep["topic_priorities"]) >= 20
    assert rep["previous_trends"]["total_previous_questions"] >= 6
    assert "নিশ্চয়তা প্রদান করে না" in rep["previous_trends"]["disclaimer"]


def test_phase5_generate_pilot_five_sets(client: TestClient, db_session: Session) -> None:
    admin = create_user_with_role(db_session, email="p5_admin@example.com", role_name="ADMIN")
    reviewer = create_user_with_role(db_session, email="p5_reviewer@example.com", role_name="REVIEWER")
    student = create_user_with_role(db_session, email="p5_student@example.com", role_name="STUDENT")

    admin_headers = auth_headers_for(admin)
    reviewer_headers = auth_headers_for(reviewer)
    student_headers = auth_headers_for(student)

    # 1. Non-admin cannot generate sets
    assert client.post("/api/v1/questions/generate-pilot-sets", headers=student_headers, json={}).status_code == 403
    assert client.post("/api/v1/questions/generate-pilot-sets", headers=reviewer_headers, json={}).status_code == 403

    # 2. Admin generates 5 pilot sets (15 questions each = 75 MCQs)
    gen_resp = client.post(
        "/api/v1/questions/generate-pilot-sets",
        headers=admin_headers,
        json={"subject_code": "BANGLA_LIT", "num_sets": 5, "questions_per_set": 15},
    )
    assert gen_resp.status_code == 201
    sets = gen_resp.json()
    assert len(sets) == 5

    for s in sets:
        assert s["target_question_count"] == 15
        assert s["question_count"] == 15
        assert s["is_published"] is False  # Unpublished until human review

    # Verify in DB: 75 GeneratedQuestions, 300 QuestionOptions, 75 AnswerKeys
    total_q = db_session.scalar(select(func.count(GeneratedQuestion.id)))
    assert total_q == 75

    total_opts = db_session.scalar(select(func.count(QuestionOption.id)))
    assert total_opts == 300

    total_keys = db_session.scalar(select(func.count(AnswerKey.id)))
    assert total_keys == 75

    # 3. Student initially sees 0 published sets
    st_list = client.get("/api/v1/questions/practice-sets", headers=student_headers).json()
    assert len(st_list) == 0

    # 4. Admin and reviewer see all 5 sets
    admin_list = client.get("/api/v1/questions/practice-sets", headers=admin_headers).json()
    assert len(admin_list) == 5

    # 5. Fetch Set 1 Detail and inspect questions
    first_set_id = sets[0]["id"]
    detail_resp = client.get(f"/api/v1/questions/practice-sets/{first_set_id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    set_detail = detail_resp.json()
    assert len(set_detail["items"]) == 15

    q1 = set_detail["items"][0]["question"]
    assert len(q1["options"]) == 4
    labels = [opt["option_label"] for opt in q1["options"]]
    assert labels == ["ক", "খ", "গ", "ঘ"]
    assert q1["answer_key"] is not None
    assert q1["answer_key"]["correct_label"] in ["ক", "খ", "গ", "ঘ"]
    assert len(q1["explanation_bn"]) > 10
    assert q1["grounding_type"] == "SOURCE_GROUNDED"

    # 6. Review question (Reviewer marks APPROVED)
    q1_id = q1["id"]
    rev_resp = client.patch(
        f"/api/v1/questions/{q1_id}/review",
        headers=reviewer_headers,
        json={"status": "APPROVED"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "APPROVED"

    # 7. Admin publishes Set 1 with custom 0.50 negative marking
    pub_resp = client.patch(
        f"/api/v1/questions/practice-sets/{first_set_id}/publish",
        headers=admin_headers,
        json={"is_published": True, "negative_mark_per_wrong": 0.50, "duration_minutes": 15},
    )
    assert pub_resp.status_code == 200
    assert pub_resp.json()["is_published"] is True

    # 8. Now student sees the published set!
    st_list_now = client.get("/api/v1/questions/practice-sets", headers=student_headers).json()
    assert len(st_list_now) == 1
    assert st_list_now[0]["id"] == first_set_id
