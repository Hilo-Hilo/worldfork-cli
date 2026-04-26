from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMRequest, LLMResponse


class LLMProviderUnavailable(RuntimeError):
    """Raised when the configured provider cannot serve a request."""


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError


class DeterministicLLMProvider(LLMProvider):
    async def complete(self, request: LLMRequest) -> LLMResponse:
        parsed = _deterministic_payload_for_purpose(request)
        return LLMResponse(
            content="Deterministic provider returned a non-LLM fallback payload.",
            parsed=parsed,
            raw={"provider": "deterministic", "purpose": request.purpose},
        )


def _deterministic_payload_for_purpose(request: LLMRequest) -> dict:
    purpose = (request.purpose or "").lower()
    if purpose.startswith("initializer_extract_chunk"):
        return {
            "entities": [],
            "groups": [],
            "events": [],
            "claims": [],
            "relationships": [],
            "uncertainties": ["Deterministic provider did not analyze source text."],
            "fallback": True,
        }
    if purpose.startswith("initializer_agent"):
        return {
            "actors": [],
            "cohorts": [],
            "heroes": [],
            "graph_edges": [],
            "sociology_baseline": [],
            "sociology_prompt_influences": [],
            "risk_flags": ["Deterministic provider did not initialize from LLM output."],
            "fallback": True,
        }
    if purpose.startswith("god_review"):
        return {
            "decision": "continue",
            "rationale": "Deterministic provider fallback; no LLM judgment was performed.",
            "confidence": 0.0,
            "tool_calls": [],
            "fallback": True,
        }
    if "report" in purpose:
        return {
            "title": None,
            "summary": "Deterministic provider fallback; no LLM report text was generated.",
            "sections": [],
            "fallback": True,
        }
    return {
        "fallback": True,
        "message": "Deterministic provider has no purpose-specific payload for this request.",
    }
