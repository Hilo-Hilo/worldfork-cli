from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMRequest, LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class DeterministicLLMProvider(LLMProvider):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content="Deterministic backend stub response.",
            parsed={"decision": "continue", "tool_calls": []},
            raw={"provider": "deterministic", "purpose": request.purpose},
        )
