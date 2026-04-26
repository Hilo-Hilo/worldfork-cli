from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.llm.provider import LLMProvider, LLMProviderUnavailable
from app.llm.schemas import LLMRequest, LLMResponse


class OpenRouterProvider(LLMProvider):
    """OpenAI-compatible OpenRouter chat-completions provider."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        settings = get_settings()
        if not settings.openrouter_api_key:
            raise LLMProviderUnavailable("LLM unavailable")

        payload = {
            "model": request.model or settings.default_model,
            "messages": request.messages,
        }
        if request.json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": request.json_schema,
            }
        else:
            payload["response_format"] = {"type": "json_object"}
        for key in ("temperature", "max_tokens", "top_p"):
            if key in request.metadata:
                payload[key] = request.metadata[key]

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://worldfork.local",
            "X-Title": "WorldFork",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                settings.openrouter_chat_completions_url,
                headers=headers,
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise LLMProviderUnavailable("LLM unavailable") from exc
            data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(content=content, raw=data)
