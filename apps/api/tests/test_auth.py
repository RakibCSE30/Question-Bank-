from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from tests.conftest import auth_headers_for, create_user_with_role


def test_argon2_password_hashing_and_verification() -> None:
    hashed = hash_password("BanglaBCS2026!")
    assert hashed.startswith("$argon2")
    assert verify_password("BanglaBCS2026!", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_register_defaults_to_student_and_prevents_duplicates(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student1@example.com",
            "full_name": "তানভীর আহমেদ",
            "password": "Password123!",
            "preferred_lang": "bn",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["role"] == "STUDENT"
    assert data["user"]["preferred_lang"] == "bn"
    assert data["access_token"]
    assert data["refresh_token"]

    dup = client.post(
        "/api/v1/auth/register",
        json={
            "email": "student1@example.com",
            "full_name": "Duplicate",
            "password": "Password123!",
        },
    )
    assert dup.status_code == 409


def test_login_and_refresh_token_rotation_and_reuse_detection(client: TestClient, db_session: Session) -> None:
    create_user_with_role(db_session, email="learner@example.com", role_name="STUDENT", password="MySecret99!")

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "learner@example.com", "password": "MySecret99!"},
    )
    assert login_resp.status_code == 200
    first_refresh = login_resp.json()["refresh_token"]

    # Rotate refresh token
    refresh_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_resp.status_code == 200
    second_refresh = refresh_resp.json()["refresh_token"]
    assert second_refresh != first_refresh

    # Reusing the old refresh token must fail AND revoke the active refresh session
    reuse_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert reuse_resp.status_code == 401

    # Even the previously valid second refresh token is now invalidated due to reuse detection
    after_reuse_resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert after_reuse_resp.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient, db_session: Session) -> None:
    create_user_with_role(db_session, email="logout@example.com", role_name="STUDENT", password="MySecret99!")
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "logout@example.com", "password": "MySecret99!"},
    )
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 204

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_after_logout.status_code == 401


def test_inactive_user_cannot_login_or_access_me(client: TestClient, db_session: Session) -> None:
    inactive_user = create_user_with_role(
        db_session,
        email="inactive@example.com",
        role_name="STUDENT",
        password="MySecret99!",
        is_active=False,
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "MySecret99!"},
    )
    assert login_resp.status_code == 403

    me_resp = client.get("/api/v1/auth/me", headers=auth_headers_for(inactive_user))
    assert me_resp.status_code == 401
