from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.logs import AuditLog
from app.workers.tasks import process_document_ingestion
from tests.conftest import auth_headers_for, create_user_with_role


def test_student_gets_403_on_all_document_endpoints(client: TestClient, db_session: Session) -> None:
    student = create_user_with_role(db_session, email="doc_student@example.com", role_name="STUDENT")
    headers = auth_headers_for(student)
    fake_id = str(uuid.uuid4())

    assert client.get("/api/v1/admin/documents", headers=headers).status_code == 403
    assert client.get(f"/api/v1/admin/documents/{fake_id}", headers=headers).status_code == 403
    assert client.post(f"/api/v1/admin/documents/{fake_id}/confirm", headers=headers).status_code == 403
    assert client.post(f"/api/v1/admin/documents/{fake_id}/reprocess-ocr", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/admin/documents/upload",
            headers=headers,
            data={"subject_id": fake_id, "title": "Blocked", "source_type": "NOTES"},
            files={"file": ("sample.txt", b"hello", "text/plain")},
        ).status_code
        == 403
    )


def test_curriculum_crud_and_bangla_literature_seed(client: TestClient, db_session: Session) -> None:
    admin = create_user_with_role(db_session, email="curr_admin@example.com", role_name="ADMIN")
    headers = auth_headers_for(admin)

    seed_resp = client.post("/api/v1/admin/subjects/seed-pilot", headers=headers)
    assert seed_resp.status_code == 200
    subj = seed_resp.json()
    assert subj["code"] == "BANGLA_LIT"
    assert subj["name_bn"] == "বাংলা সাহিত্য"
    assert subj["name_en"] == "Bangla Literature"

    # Idempotent re-seed
    seed_again = client.post("/api/v1/admin/subjects/seed-pilot", headers=headers)
    assert seed_again.status_code == 200
    assert seed_again.json()["id"] == subj["id"]

    # Create chapter
    chap_resp = client.post(
        f"/api/v1/admin/subjects/{subj['id']}/chapters",
        headers=headers,
        json={"order_index": 1, "title_bn": "প্রাচীন যুগ", "title_en": "Ancient Period"},
    )
    assert chap_resp.status_code == 201
    chap_id = chap_resp.json()["id"]

    list_chaps = client.get(f"/api/v1/subjects/{subj['id']}/chapters", headers=headers)
    assert list_chaps.status_code == 200
    assert len(list_chaps.json()) == 1
    assert list_chaps.json()[0]["id"] == chap_id


def test_document_upload_duplicate_and_flagged_confirmation_workflow(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()

    # Stub Celery .delay() so tests run synchronously without Redis broker
    dispatched: list[tuple[str, bool]] = []

    class _StubTask:
        @staticmethod
        def delay(doc_id: str, force_ocr: bool = False) -> None:
            dispatched.append((doc_id, force_ocr))

    monkeypatch.setattr("app.api.v1.routers.documents.ingest_document_task", _StubTask)

    admin = create_user_with_role(db_session, email="upload_admin@example.com", role_name="ADMIN")
    headers = auth_headers_for(admin)

    subj_id = client.post("/api/v1/admin/subjects/seed-pilot", headers=headers).json()["id"]

    # 1. Clean Unicode synthetic document -> COMPLETED & usable
    clean_bytes = (
        "প্রথম অধ্যায়: নমুনা পাঠ। এটি একটি কৃত্রিম ইউনিকোড বাংলা অনুচ্ছেদ। "
        "এটি শুধুমাত্র আপলোড এবং চাঙ্কিং পরীক্ষার জন্য তৈরি করা হয়েছে।"
    ).encode("utf-8")

    up_ok = client.post(
        "/api/v1/admin/documents/upload",
        headers=headers,
        data={"subject_id": subj_id, "title": "Synthetic Clean Notes", "source_type": "NOTES"},
        files={"file": ("clean.txt", clean_bytes, "text/plain")},
    )
    assert up_ok.status_code == 201
    clean_doc_id = up_ok.json()["id"]
    assert len(dispatched) == 1

    # Duplicate SHA-256 upload must fail with 409
    dup = client.post(
        "/api/v1/admin/documents/upload",
        headers=headers,
        data={"subject_id": subj_id, "title": "Duplicate Notes", "source_type": "NOTES"},
        files={"file": ("clean_copy.txt", clean_bytes, "text/plain")},
    )
    assert dup.status_code == 409

    # Run ingestion synchronously in test DB
    process_document_ingestion(db_session, uuid.UUID(clean_doc_id))
    detail_clean = client.get(f"/api/v1/admin/documents/{clean_doc_id}", headers=headers)
    assert detail_clean.status_code == 200
    body_clean = detail_clean.json()
    assert body_clean["ingestion_status"] == "COMPLETED"
    assert body_clean["usable_for_generation"] is True
    assert body_clean["chunk_count"] >= 1
    assert body_clean["chunks"][0]["page_number"] == 1

    # 2. Low-quality Bijoy-garbled synthetic document -> FLAGGED & blocked until Admin confirms
    garbled_bytes = (
        "Avgvi †mvbvi evsjv, Avwg †Zvgvq fv‡jvevwm। "
        "cÖkœcÎ I mvwnZ¨ cvV¨µg hvPvB‡qi Rb¨ K…wÎg bgybv।"
    ).encode("utf-8")

    up_bad = client.post(
        "/api/v1/admin/documents/upload",
        headers=headers,
        data={"subject_id": subj_id, "title": "Synthetic Bijoy Fixture", "source_type": "TEXTBOOK"},
        files={"file": ("garbled.txt", garbled_bytes, "text/plain")},
    )
    assert up_bad.status_code == 201
    bad_doc_id = up_bad.json()["id"]

    process_document_ingestion(db_session, uuid.UUID(bad_doc_id))
    detail_bad = client.get(f"/api/v1/admin/documents/{bad_doc_id}", headers=headers).json()
    assert detail_bad["ingestion_status"] == "FLAGGED"
    assert detail_bad["legacy_encoding_detected"] is True
    assert detail_bad["extraction_quality_score"] < 0.70
    assert detail_bad["usable_for_generation"] is False

    # usable_only=true MUST exclude unconfirmed FLAGGED documents
    usable_list = client.get("/api/v1/admin/documents?usable_only=true", headers=headers).json()
    usable_ids = {d["id"] for d in usable_list["items"]}
    assert clean_doc_id in usable_ids
    assert bad_doc_id not in usable_ids

    # Admin explicitly confirms the FLAGGED document
    confirm_resp = client.post(f"/api/v1/admin/documents/{bad_doc_id}/confirm", headers=headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["admin_confirmed_low_quality"] is True
    assert confirm_resp.json()["usable_for_generation"] is True

    usable_after = client.get("/api/v1/admin/documents?usable_only=true", headers=headers).json()
    assert bad_doc_id in {d["id"] for d in usable_after["items"]}

    logs = db_session.scalars(select(AuditLog)).all()
    assert any(l.action == "FLAGGED_DOCUMENT_CONFIRMED" for l in logs)
    get_settings.cache_clear()
