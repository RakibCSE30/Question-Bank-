from __future__ import annotations


class AIConfigurationError(RuntimeError):
    """Raised when an AI/embedding provider or API key is missing or misconfigured."""


class AIProviderError(RuntimeError):
    """Raised when an upstream AI provider call fails or returns invalid output."""
