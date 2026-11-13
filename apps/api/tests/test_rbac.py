from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.logs import AuditLog
from tests.conftest import auth_headers_for, create_user_with_role


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/dashboard/student").status_code == 401
    assert client.get("/api/v1/dashboard/reviewer").status_code == 401
    assert client.get("/api/v1/dashboard/admin").status_code == 401
    assert client.get("/api/v1/admin/users").status_code == 401


def test_student_rbac_boundaries(client: TestClient, db_session: Session) -> None:
    student = create_user_with_role(db_session, email="s@example.com", role_name="STUDENT")
    headers = auth_headers_for(student)

    assert client.get("/api/v1/dashboard/student", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/reviewer", headers=headers).status_code == 403
    assert client.get("/api/v1/dashboard/admin", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/users",
            headers=headers,
            json={
                "email": "evil@example.com",
                "full_name": "Evil",
                "password": "Password123!",
                "role": "ADMIN",
            },
        ).status_code
        == 403
    )


def test_reviewer_rbac_boundaries(client: TestClient, db_session: Session) -> None:
    reviewer = create_user_with_role(db_session, email="r@example.com", role_name="REVIEWER")
    headers = auth_headers_for(reviewer)

    assert client.get("/api/v1/dashboard/student", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/reviewer", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/admin", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403


def test_admin_user_management_and_audit_logging(client: TestClient, db_session: Session) -> None:
    admin = create_user_with_role(db_session, email="a@example.com", role_name="ADMIN")
    headers = auth_headers_for(admin)

    assert client.get("/api/v1/dashboard/admin", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/reviewer", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard/student", headers=headers).status_code == 200

    # Admin creates a REVIEWER user
    create_resp = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "new_reviewer@example.com",
            "full_name": "নাজমুল হক",
            "password": "ReviewerPass123!",
            "role": "REVIEWER",
            "preferred_lang": "bn",
        },
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]
    assert create_resp.json()["role"] == "REVIEWER"

    # Admin promotes / deactivates user
    patch_resp = client.patch(
        f"/api/v1/admin/users/{created_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False

    # Admin cannot deactivate themselves
    self_deactivate = client.patch(
        f"/api/v1/admin/users/{admin.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert self_deactivate.status_code == 400

    # Audit log must capture both creation and update
    logs = db_session.scalars(select(AuditLog).order_by(AuditLog.created_at.asc())).all()
    actions = [log.action for log in logs]
    assert "ADMIN_CREATED_USER" in actions
    assert "ADMIN_UPDATED_USER" in actions
