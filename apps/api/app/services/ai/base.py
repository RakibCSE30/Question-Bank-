from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMResponseMetadata(BaseModel):
    provider: str
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class LLMProvider(ABC):
    """Config-switchable LLM provider interface (implemented in Phase 3+)."""

    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        model_name: str,
        temperature: float,
    ) -> tuple[T, LLMResponseMetadata]:
        raise NotImplementedError


class EmbeddingProvider(ABC):
    """Config-switchable multilingual embedding provider interface (OpenAI / BGE-M3 in Phase 3+)."""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError
