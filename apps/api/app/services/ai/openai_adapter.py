from __future__ import annotations

import time
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.services.ai.base import EmbeddingProvider, LLMProvider, LLMResponseMetadata
from app.services.ai.exceptions import AIConfigurationError, AIProviderError

T = TypeVar("T", bound=BaseModel)

_OPENAI_EMBED_DIMS: dict[str, int] = {
    "text-embedding-3-large": 3072,
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
}


class OpenAILLMProvider(LLMProvider):
    def __init__(self, *, api_key: str) -> None:
        if not api_key or not api_key.strip():
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured. Add it to your .env file to enable LLM calls."
            )
        self._client = OpenAI(api_key=api_key.strip())

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[T],
        model_name: str,
        temperature: float,
    ) -> tuple[T, LLMResponseMetadata]:
        started = time.perf_counter()
        try:
            completion = self._client.beta.chat.completions.parse(
                model=model_name,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_schema,
            )
        except Exception as exc:
            raise AIProviderError(f"OpenAI structured completion failed: {type(exc).__name__}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        message = completion.choices[0].message
        parsed = getattr(message, "parsed", None)
        if parsed is None:
            raw_content = message.content or ""
            try:
                parsed = response_schema.model_validate_json(raw_content)
            except Exception as exc:
                raise AIProviderError("OpenAI response did not match required JSON schema.") from exc

        usage = completion.usage
        meta = LLMResponseMetadata(
            provider="openai",
            model_name=model_name,
            input_tokens=int(usage.prompt_tokens) if usage and usage.prompt_tokens else 0,
            output_tokens=int(usage.completion_tokens) if usage and usage.completion_tokens else 0,
            latency_ms=elapsed_ms,
        )
        return parsed, meta


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, *, api_key: str, model_name: str = "text-embedding-3-large") -> None:
        if not api_key or not api_key.strip():
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured. Add it to your .env file or switch EMBEDDING_PROVIDER."
            )
        self._client = OpenAI(api_key=api_key.strip())
        self._model_name = model_name
        self._dimension = _OPENAI_EMBED_DIMS.get(model_name, 3072)

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        batch_size = 64
        try:
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                resp = self._client.embeddings.create(
                    model=self._model_name,
                    input=batch,
                )
                vectors.extend([item.embedding for item in resp.data])
        except Exception as exc:
            raise AIProviderError(f"OpenAI embedding request failed: {type(exc).__name__}") from exc
        return vectors
