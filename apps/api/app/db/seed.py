from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models.users import Role, User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

SYSTEM_ROLES: dict[str, str] = {
    "ADMIN": "System administrator: users, curriculum, documents, generation, marking rules, reports",
    "REVIEWER": "Human quality reviewer: inspect citations, edit, approve or reject questions",
    "STUDENT": "Learner: take approved mock tests, view analytics and written practice",
}


def ensure_roles_seeded(db: Session) -> dict[str, Role]:
    existing = {role.name: role for role in db.scalars(select(Role)).all()}
    for name, description in SYSTEM_ROLES.items():
        if name not in existing:
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()
            existing[name] = role
    db.commit()
    return existing


def seed_initial_admin_if_configured(db: Session) -> None:
    settings = get_settings()
    roles = ensure_roles_seeded(db)

    email = settings.INITIAL_ADMIN_EMAIL.strip().lower()
    password = settings.INITIAL_ADMIN_PASSWORD.strip()
    if not email or not password:
        logger.info("INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD not set; skipping admin bootstrap.")
        return

    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user:
        logger.info("Initial admin user already exists.")
        return

    admin_user = User(
        email=email,
        full_name=settings.INITIAL_ADMIN_NAME.strip() or "System Admin",
        password_hash=hash_password(password),
        role_id=roles["ADMIN"].id,
        preferred_lang="bn",
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    logger.info("Bootstrapped initial ADMIN user from environment configuration.")


def main() -> None:
    with SessionLocal() as db:
        seed_initial_admin_if_configured(db)


if __name__ == "__main__":
    main()
