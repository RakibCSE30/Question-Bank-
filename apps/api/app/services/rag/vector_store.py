from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import get_settings


@dataclass(frozen=True)
class ChunkVectorPoint:
    point_id: str
    chunk_id: str
    document_id: str
    document_title: str
    subject_id: str
    chapter_id: str | None
    page_number: int
    heading_path: str | None
    source_type: str
    usable_for_generation: bool
    vector: list[float]


@dataclass(frozen=True)
class VectorSearchHit:
    chunk_id: str
    document_id: str
    document_title: str
    page_number: int
    heading_path: str | None
    source_type: str
    usable_for_generation: bool
    score: float


class QdrantVectorStore:
    def __init__(
        self,
        *,
        client: QdrantClient | None = None,
        collection_name: str | None = None,
    ) -> None:
        settings = get_settings()
        self._collection = collection_name or settings.QDRANT_COLLECTION_CHUNKS
        self._client = client or QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
            timeout=10.0,
        )

    def ensure_collection(self, vector_size: int) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
            )
            for field_name, schema in (
                ("subject_id", qm.PayloadSchemaType.KEYWORD),
                ("chapter_id", qm.PayloadSchemaType.KEYWORD),
                ("document_id", qm.PayloadSchemaType.KEYWORD),
                ("usable_for_generation", qm.PayloadSchemaType.BOOL),
            ):
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field_name,
                    field_schema=schema,
                )

    def upsert_chunks(self, points: list[ChunkVectorPoint]) -> None:
        if not points:
            return
        self.ensure_collection(len(points[0].vector))
        qdrant_points = [
            qm.PointStruct(
                id=p.point_id,
                vector=p.vector,
                payload={
                    "chunk_id": p.chunk_id,
                    "document_id": p.document_id,
                    "document_title": p.document_title,
                    "subject_id": p.subject_id,
                    "chapter_id": p.chapter_id,
                    "page_number": p.page_number,
                    "heading_path": p.heading_path,
                    "source_type": p.source_type,
                    "usable_for_generation": p.usable_for_generation,
                },
            )
            for p in points
        ]
        self._client.upsert(collection_name=self._collection, points=qdrant_points)

    def update_document_usability(self, document_id: uuid.UUID, usable_for_generation: bool) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            return
        self._client.set_payload(
            collection_name=self._collection,
            payload={"usable_for_generation": usable_for_generation},
            points=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )

    def delete_document_vectors(self, document_id: uuid.UUID) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            return
        self._client.delete(
            collection_name=self._collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
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
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            return []

        must_conditions: list[Any] = [
            qm.FieldCondition(key="subject_id", match=qm.MatchValue(value=str(subject_id)))
        ]
        if chapter_id is not None:
            must_conditions.append(
                qm.FieldCondition(key="chapter_id", match=qm.MatchValue(value=str(chapter_id)))
            )
        if usable_only:
            must_conditions.append(
                qm.FieldCondition(key="usable_for_generation", match=qm.MatchValue(value=True))
            )

        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=qm.Filter(must=must_conditions),
            limit=top_k,
            with_payload=True,
        )
        hits: list[VectorSearchHit] = []
        for point in response.points:
            payload = point.payload or {}
            hits.append(
                VectorSearchHit(
                    chunk_id=str(payload.get("chunk_id", point.id)),
                    document_id=str(payload.get("document_id", "")),
                    document_title=str(payload.get("document_title", "")),
                    page_number=int(payload.get("page_number", 1)),
                    heading_path=payload.get("heading_path"),
                    source_type=str(payload.get("source_type", "")),
                    usable_for_generation=bool(payload.get("usable_for_generation", False)),
                    score=float(point.score),
                )
            )
        return hits
