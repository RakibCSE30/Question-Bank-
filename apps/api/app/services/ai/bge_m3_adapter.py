from __future__ import annotations

from typing import Any

from app.services.ai.base import EmbeddingProvider
from app.services.ai.exceptions import AIConfigurationError, AIProviderError


class BgeM3EmbeddingProvider(EmbeddingProvider):
    """Local multilingual embedding adapter using BAAI/bge-m3 via sentence-transformers."""

    def __init__(self, *, model_name: str = "BAAI/bge-m3") -> None:
        self._model_name = model_name
        self._model: Any = None
        self._dimension = 1024

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise AIConfigurationError(
                "sentence-transformers is not installed. Install optional extra '.[bge]' to use BAAI/bge-m3."
            ) from exc

        try:
            self._model = SentenceTransformer(self._model_name)
        except Exception as exc:
            raise AIProviderError(f"Failed to load embedding model '{self._model_name}'.") from exc
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        try:
            encoded = model.encode(texts, normalize_embeddings=True)
            return [row.tolist() if hasattr(row, "tolist") else list(row) for row in encoded]
        except Exception as exc:
            raise AIProviderError(f"BGE-M3 embedding inference failed: {type(exc).__name__}") from exc
