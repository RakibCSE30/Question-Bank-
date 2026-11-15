from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.curriculum import Subject, SyllabusItem
from app.db.models.documents import Document, DocumentChunk
from app.db.models.logs import AIGenerationLog
from app.services.ai.base import EmbeddingProvider, LLMProvider, LLMResponseMetadata
from app.services.ai.bge_m3_adapter import BgeM3EmbeddingProvider
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.registry import get_ai_configuration_status, get_embedding_provider, get_llm_provider
from app.services.analysis.syllabus_analyzer import SyllabusExtractionOutput, ExtractedSyllabusTopic, analyze_syllabus_document
from app.services.rag.benchmark import RetrievalEvalQuery, benchmark_embedding_provider
from app.services.rag.retriever import index_document_chunks, retrieve_relevant_chunks
from app.services.rag.vector_store import ChunkVectorPoint, VectorSearchHit
from tests.conftest import auth_headers_for, create_user_with_role


class _FakeEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 3

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            if "চর্যাপদ" in text or "প্রাচীন" in text:
                vectors.append([1.0, 0.0, 0.0])
            elif "রবীন্দ্রনাথ" in text or "গীতাঞ্জলি" in text:
                vectors.append([0.0, 1.0, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


class _InMemoryVectorStore:
    def __init__(self) -> None:
        self.points: dict[str, ChunkVectorPoint] = {}

    def delete_document_vectors(self, document_id: uuid.UUID) -> None:
        doc_str = str(document_id)
        self.points = {k: v for k, v in self.points.items() if v.document_id != doc_str}

    def upsert_chunks(self, points: list[ChunkVectorPoint]) -> None:
        for p in points:
            self.points[p.point_id] = p

    def update_document_usability(self, document_id: uuid.UUID, usable_for_generation: bool) -> None:
        doc_str = str(document_id)
        for pid, p in list(self.points.items()):
            if p.document_id == doc_str:
                self.points[pid] = ChunkVectorPoint(
                    point_id=p.point_id,
                    chunk_id=p.chunk_id,
                    document_id=p.document_id,
                    document_title=p.document_title,
                    subject_id=p.subject_id,
                    chapter_id=p.chapter_id,
                    page_number=p.page_number,
                    heading_path=p.heading_path,
                    source_type=p.source_type,
                    usable_for_generation=usable_for_generation,
                    vector=p.vector,
                )

    def search_chunks(
        self,
        *,
        query_vector: list[float],
        subject_id: uuid.UUID,
        chapter_id: uuid.UUID | None = None,
        top_k: int = 5,
        usable_only: bool = True,
    ) -> list[VectorSearchHit]:
        hits: list[VectorSearchHit] = []
        for p in self.points.values():
            if p.subject_id != str(subject_id):
                continue
            if chapter_id is not None and p.chapter_id != str(chapter_id):
                continue
            if usable_only and not p.usable_for_generation:
                continue
            score = sum(a * b for a, b in zip(query_vector, p.vector, strict=True))
            hits.append(
                VectorSearchHit(
                    chunk_id=p.chunk_id,
                    document_id=p.document_id,
                    document_title=p.document_title,
                    page_number=p.page_number,
                    heading_path=p.heading_path,
                    source_type=p.source_type,
                    usable_for_generation=p.usable_for_generation,
                    score=float(score),
                )
            )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


class _FakeLLMProvider(LLMProvider):
    def generate_structured(self, *, system_prompt, user_prompt, response_schema, model_name, temperature):
        parsed = SyllabusExtractionOutput(
            items=[
                ExtractedSyllabusTopic(
                    topic_bn="প্রাচীন যুগ ও চর্যাপদ",
                    topic_en="Ancient Period and Charyapada",
                    weight_percentage=25.0,
                    priority="HIGH",
                    priority_reason="Cited in syllabus page 1",
                    source_reference="Page 1",
                )
            ]
        )
        meta = LLMResponseMetadata(
            provider="fake",
            model_name=model_name,
            input_tokens=120,
            output_tokens=45,
            latency_ms=10,
        )
        return parsed, meta


def test_missing_openai_key_raises_clear_error_and_status_never_leaks_secret(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    get_settings.cache_clear()

    with pytest.raises(AIConfigurationError, match="OPENAI_API_KEY"):
        get_llm_provider()

    with pytest.raises(AIConfigurationError, match="OPENAI_API_KEY"):
        get_embedding_provider()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value-never-expose")
    get_settings.cache_clear()
    status_dict = get_ai_configuration_status()
    assert status_dict["openai_api_key_configured"] is True
    assert "sk-super-secret" not in str(status_dict)
    get_settings.cache_clear()


def test_embedding_provider_registry_switches_to_bge_m3(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "sentence_transformers")
    get_settings.cache_clear()
    provider = get_embedding_provider()
    assert isinstance(provider, BgeM3EmbeddingProvider)
    assert provider.dimension == 1024
    get_settings.cache_clear()


def test_rag_endpoints_enforce_rbac_and_missing_key_returns_503(
    client: TestClient,
    db_session: Session,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()

    student = create_user_with_role(db_session, email="rag_student@example.com", role_name="STUDENT")
    admin = create_user_with_role(db_session, email="rag_admin@example.com", role_name="ADMIN")

    student_headers = auth_headers_for(student)
    admin_headers = auth_headers_for(admin)
    fake_id = str(uuid.uuid4())

    # Student blocked from AI/RAG endpoints
    assert client.get("/api/v1/ai/status", headers=student_headers).status_code == 403
    assert (
        client.post(
            "/api/v1/rag/retrieve",
            headers=student_headers,
            json={"query": "চর্যাপদ", "subject_id": fake_id},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/admin/syllabus/analyze",
            headers=student_headers,
            json={"document_id": fake_id},
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/admin/documents/{fake_id}", headers=student_headers).status_code == 403

    # Admin gets clear 503 when OPENAI_API_KEY is missing
    retrieve_resp = client.post(
        "/api/v1/rag/retrieve",
        headers=admin_headers,
        json={"query": "চর্যাপদ", "subject_id": fake_id},
    )
    assert retrieve_resp.status_code == 503
    assert "OPENAI_API_KEY" in retrieve_resp.json()["detail"]
    get_settings.cache_clear()


def test_vector_indexing_retrieval_respects_flagged_gate_and_benchmark(db_session: Session) -> None:
    admin = create_user_with_role(db_session, email="vec_admin@example.com", role_name="ADMIN")
    subj = Subject(code="BANGLA_LIT", name_bn="বাংলা সাহিত্য", name_en="Bangla Literature", bcs_total_marks=20)
    db_session.add(subj)
    db_session.flush()

    usable_doc = Document(
        uploaded_by=admin.id,
        subject_id=subj.id,
        title="Usable Synthetic Notes",
        source_type="NOTES",
        file_name="notes.txt",
        mime_type="text/plain",
        file_size_bytes=100,
        sha256_hash="a" * 64,
        storage_path="/tmp/a.txt",
        extraction_method="TXT",
        extraction_quality_score=Decimal("0.950"),
        ingestion_status="COMPLETED",
    )
    flagged_doc = Document(
        uploaded_by=admin.id,
        subject_id=subj.id,
        title="Flagged Synthetic Notes",
        source_type="NOTES",
        file_name="flagged.txt",
        mime_type="text/plain",
        file_size_bytes=100,
        sha256_hash="b" * 64,
        storage_path="/tmp/b.txt",
        extraction_method="TXT",
        extraction_quality_score=Decimal("0.400"),
        ingestion_status="FLAGGED",
        admin_confirmed_low_quality=False,
    )
    db_session.add_all([usable_doc, flagged_doc])
    db_session.flush()

    c1 = DocumentChunk(
        document_id=usable_doc.id,
        subject_id=subj.id,
        chunk_index=0,
        page_number=1,
        heading_path="প্রাচীন যুগ",
        content_nfc="চর্যাপদ বাংলা সাহিত্যের প্রাচীনতম নিদর্শন।",
        token_count=6,
    )
    c2 = DocumentChunk(
        document_id=flagged_doc.id,
        subject_id=subj.id,
        chunk_index=0,
        page_number=2,
        heading_path="অস্পষ্ট",
        content_nfc="চর্যাপদ সম্পর্কিত অস্পষ্ট স্ক্যান করা অংশ।",
        token_count=6,
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    store = _InMemoryVectorStore()
    embedder = _FakeEmbeddingProvider()

    assert index_document_chunks(db_session, usable_doc, usable_for_generation=True, embedding_provider=embedder, vector_store=store) == 1
    assert index_document_chunks(db_session, flagged_doc, usable_for_generation=False, embedding_provider=embedder, vector_store=store) == 1

    # Retrieval with usable_only=True excludes unconfirmed FLAGGED doc
    hits = retrieve_relevant_chunks(
        db_session,
        query="চর্যাপদ প্রাচীন",
        subject_id=subj.id,
        usable_only=True,
        embedding_provider=embedder,
        vector_store=store,
    )
    assert len(hits) == 1
    assert hits[0].document_id == usable_doc.id

    # Benchmark MRR@k and Recall@k on synthetic Bengali corpus
    bench = benchmark_embedding_provider(
        provider_name="fake-bengali",
        provider=embedder,
        passages={
            "p1": "চর্যাপদ প্রাচীন বাংলা নিদর্শন।",
            "p2": "রবীন্দ্রনাথ ঠাকুর গীতাঞ্জলি রচনা করেন।",
        },
        eval_queries=[
            RetrievalEvalQuery(query_bn="চর্যাপদ প্রাচীন যুগ", relevant_passage_ids={"p1"}),
            RetrievalEvalQuery(query_bn="গীতাঞ্জলি রবীন্দ্রনাথ", relevant_passage_ids={"p2"}),
        ],
        top_k=1,
    )
    assert bench.mrr_at_k == 1.0
    assert bench.recall_at_k == 1.0

    # Syllabus analysis persists SyllabusItem and AIGenerationLog
    items = analyze_syllabus_document(
        db_session,
        document=usable_doc,
        triggered_by=admin.id,
        llm_provider=_FakeLLMProvider(),
    )
    assert len(items) == 1
    assert db_session.query(SyllabusItem).count() == 1
    logs = db_session.scalars(select(AIGenerationLog)).all()
    assert len(logs) == 1
    assert logs[0].stage == "CONTENT_ANALYSIS"
    assert logs[0].status == "SUCCESS"
