from __future__ import annotations

import importlib.util
from typing import Any

from app.core.config import get_settings
from app.services.ai.base import EmbeddingProvider, LLMProvider
from app.services.ai.bge_m3_adapter import BgeM3EmbeddingProvider
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.openai_adapter import OpenAIEmbeddingProvider, OpenAILLMProvider


def get_llm_provider(provider_override: str | None = None) -> LLMProvider:
    settings = get_settings()
    provider = (provider_override or settings.LLM_PROVIDER).strip().lower()
    if provider == "openai":
        return OpenAILLMProvider(api_key=settings.OPENAI_API_KEY)
    raise AIConfigurationError(
        f"Unsupported LLM_PROVIDER '{provider}'. Currently supported: openai."
    )


def get_embedding_provider(provider_override: str | None = None) -> EmbeddingProvider:
    settings = get_settings()
    provider = (provider_override or settings.EMBEDDING_PROVIDER).strip().lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.EMBEDDING_MODEL,
        )
    if provider in ("sentence_transformers", "bge_m3", "bge-m3"):
        return BgeM3EmbeddingProvider(model_name=settings.BGE_M3_MODEL)
    raise AIConfigurationError(
        f"Unsupported EMBEDDING_PROVIDER '{provider}'. Supported: openai, sentence_transformers."
    )


def get_ai_configuration_status() -> dict[str, Any]:
    """Return non-secret AI/vector configuration flags (never exposes API keys)."""
    settings = get_settings()
    bge_installed = importlib.util.find_spec("sentence_transformers") is not None
    openai_configured = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())

    active_embed_ready = (
        openai_configured
        if settings.EMBEDDING_PROVIDER.strip().lower() == "openai"
        else bge_installed
    )
    active_llm_ready = (
        openai_configured
        if settings.LLM_PROVIDER.strip().lower() == "openai"
        else False
    )

    return {
        "llm_provider": settings.LLM_PROVIDER,
        "generation_model": settings.GENERATION_MODEL,
        "verification_model": settings.VERIFICATION_MODEL,
        "verification_temperature": settings.VERIFICATION_TEMPERATURE,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "bge_m3_model": settings.BGE_M3_MODEL,
        "openai_api_key_configured": openai_configured,
        "bge_m3_installed": bge_installed,
        "llm_ready": active_llm_ready,
        "embedding_ready": active_embed_ready,
    }
