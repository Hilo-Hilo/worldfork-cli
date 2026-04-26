"""Ollama provider — local LLM adapter via the OpenAI-compatible endpoint.

Ollama exposes an OpenAI-compatible /v1/chat/completions on
``http://localhost:11434/v1``, so we reuse :class:`OpenRouterProvider` with a
different base URL and a dummy api_key.

TODO B5+: handle Ollama-specific response_format quirks (most local models
don't honor json_schema), and surface model-pull errors gracefully.
"""
from __future__ import annotations

from backend.app.providers.openrouter import OpenRouterProvider


class OllamaProvider(OpenRouterProvider):
    """Local Ollama adapter — OpenAI-compatible endpoint."""

    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434/v1",
        default_model: str = "llama3.1:8b",
        fallback_model: str | None = None,
        request_timeout: float = 300.0,
    ) -> None:
        super().__init__(
            api_key="ollama",  # Ollama ignores the key but the SDK requires non-empty.
            base_url=base_url,
            default_model=default_model,
            fallback_model=fallback_model,
            http_referer="http://localhost:8003",
            x_title="WorldFork",
            request_timeout=request_timeout,
        )
