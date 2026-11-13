from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
import app.db.models  # noqa: F401
from app.db.models.users import Role, User
from app.db.seed import ensure_roles_seeded
from app.db.session import get_db
from app.main import create_app


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    test_db_url = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    connect_args = {"check_same_thread": False} if test_db_url.startswith("sqlite") else {}
    pool_kwargs = {"poolclass": StaticPool} if ":memory:" in test_db_url else {}

    engine = create_engine(test_db_url, connect_args=connect_args, **pool_kwargs)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    db = TestingSessionLocal()
    try:
        ensure_roles_seeded(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


def create_user_with_role(db: Session, *, email: str, role_name: str, password: str = "StrongPass123!", is_active: bool = True) -> User:
    role = db.query(Role).filter(Role.name == role_name).one()
    user = User(
        email=email.lower(),
        full_name=f"{role_name.title()} User",
        password_hash=hash_password(password),
        role_id=role.id,
        preferred_lang="bn",
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user.role = role
    return user


def auth_headers_for(user: User) -> dict[str, str]:
    token, _ = create_access_token(user_id=user.id, role=user.role.name)
    return {"Authorization": f"Bearer {token}"}
