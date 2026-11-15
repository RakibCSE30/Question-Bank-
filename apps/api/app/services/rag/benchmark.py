from __future__ import annotations

import math
from dataclasses import dataclass

from app.services.ai.base import EmbeddingProvider


@dataclass(frozen=True)
class RetrievalEvalQuery:
    query_bn: str
    relevant_passage_ids: set[str]


@dataclass(frozen=True)
class ProviderBenchmarkResult:
    provider_name: str
    dimension: int
    mrr_at_k: float
    recall_at_k: float
    top_k: int


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def benchmark_embedding_provider(
    *,
    provider_name: str,
    provider: EmbeddingProvider,
    passages: dict[str, str],
    eval_queries: list[RetrievalEvalQuery],
    top_k: int = 3,
) -> ProviderBenchmarkResult:
    """Evaluate a Bengali embedding provider using MRR@k and Recall@k on synthetic or curated pairs."""
    if not passages or not eval_queries:
        return ProviderBenchmarkResult(
            provider_name=provider_name,
            dimension=provider.dimension,
            mrr_at_k=0.0,
            recall_at_k=0.0,
            top_k=top_k,
        )

    passage_ids = list(passages.keys())
    passage_vecs = provider.embed_texts([passages[pid] for pid in passage_ids])
    query_vecs = provider.embed_texts([q.query_bn for q in eval_queries])

    total_rr = 0.0
    total_recall = 0.0

    for q, q_vec in zip(eval_queries, query_vecs, strict=True):
        scored = [
            (pid, _cosine_similarity(q_vec, p_vec))
            for pid, p_vec in zip(passage_ids, passage_vecs, strict=True)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [pid for pid, _ in scored[:top_k]]

        rr = 0.0
        for rank, pid in enumerate(top_ids, start=1):
            if pid in q.relevant_passage_ids:
                rr = 1.0 / rank
                break
        total_rr += rr

        hits = len(set(top_ids) & q.relevant_passage_ids)
        total_recall += hits / max(1, len(q.relevant_passage_ids))

    n = len(eval_queries)
    return ProviderBenchmarkResult(
        provider_name=provider_name,
        dimension=provider.dimension,
        mrr_at_k=round(total_rr / n, 4),
        recall_at_k=round(total_recall / n, 4),
        top_k=top_k,
    )
