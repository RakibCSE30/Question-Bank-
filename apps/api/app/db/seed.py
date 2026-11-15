from __future__ import annotations

import argparse
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models.curriculum import Subject
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


def seed_bangla_literature(db: Session) -> tuple[Subject, bool]:
    """Create ONLY the pilot subject 'Bangla Literature' (বাংলা সাহিত্য). No fake docs or questions."""
    existing = db.scalar(select(Subject).where(Subject.code == "BANGLA_LIT"))
    if existing is not None:
        return existing, False

    subject = Subject(
        code="BANGLA_LIT",
        name_bn="বাংলা সাহিত্য",
        name_en="Bangla Literature",
        bcs_total_marks=20,
        is_active=True,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject, True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Smart Question Bank baseline records.")
    parser.add_argument(
        "--pilot-subject",
        action="store_true",
        help="Also seed the 'Bangla Literature' (বাংলা সাহিত্য) subject only.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        seed_initial_admin_if_configured(db)
        if args.pilot_subject:
            subject, created = seed_bangla_literature(db)
            status_msg = "created" if created else "already exists"
            print(f"Pilot subject '{subject.name_en}' ({subject.name_bn}) {status_msg}.")


if __name__ == "__main__":
    main()
