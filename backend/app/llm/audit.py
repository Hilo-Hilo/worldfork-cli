from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models
from app.llm.openrouter_provider import OpenRouterProvider
from app.llm.provider import DeterministicLLMProvider, LLMProvider
from app.llm.redaction import redact_payload
from app.llm.schemas import LLMRequest, LLMResponse
from app.storage.artifact_store import ArtifactStore


def provider_for_settings() -> LLMProvider:
    settings = get_settings()
    if settings.default_llm_provider == "openrouter" and settings.openrouter_api_key:
        return OpenRouterProvider()
    return DeterministicLLMProvider()


def parse_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return {"text": content}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"text": content}


def complete_with_audit(
    db: Session,
    *,
    big_bang_id,
    purpose: str,
    model: str,
    messages: list[dict[str, str]],
    metadata: dict[str, Any] | None = None,
    json_schema: dict[str, Any] | None = None,
) -> tuple[LLMResponse, models.LLMCall]:
    store = ArtifactStore()
    metadata = metadata or {}
    request_payload = {
        "purpose": purpose,
        "model": model,
        "messages": messages,
        "json_schema": json_schema,
        "metadata": metadata,
    }
    sanitized_request = redact_payload(request_payload)
    request_artifact = store.write_json(
        db,
        big_bang_id=big_bang_id,
        relative_path=f"big_bang_{big_bang_id}/sanitized_llm_calls/{purpose}_request.json",
        payload=sanitized_request,
        kind="llm_request_sanitized",
    )
    raw_request_artifact = store.write_json(
        db,
        big_bang_id=big_bang_id,
        relative_path=f"big_bang_{big_bang_id}/raw_llm_calls/{purpose}_request.json",
        payload=request_payload,
        kind="llm_request_raw",
        debug_only=True,
    )
    call = models.LLMCall(
        big_bang_id=big_bang_id,
        provider=get_settings().default_llm_provider,
        model=model,
        purpose=purpose,
        status="running",
        request_artifact_id=request_artifact.id,
        meta={"raw_request_artifact_id": str(raw_request_artifact.id), **metadata},
    )
    db.add(call)
    db.flush()
    settings = get_settings()
    attempts: list[dict[str, Any]] = []
    response: LLMResponse | None = None
    last_error: Exception | None = None
    max_retries = max(1, settings.llm_max_retries)
    for attempt in range(1, max_retries + 1):
        try:
            response = asyncio.run(
                provider_for_settings().complete(
                    LLMRequest(
                        purpose=purpose,
                        model=model,
                        messages=messages,
                        json_schema=json_schema,
                        metadata=metadata,
                    )
                )
            )
            if not response.content and not response.parsed:
                raise RuntimeError("LLM response was empty")
            attempts.append({"attempt": attempt, "status": "succeeded"})
            break
        except Exception as exc:
            last_error = exc
            attempts.append({"attempt": attempt, "status": "failed", "error": str(exc)})
            if attempt < max_retries:
                time.sleep(settings.llm_retry_backoff_seconds * attempt)
    try:
        if response is None:
            raise RuntimeError(str(last_error) if last_error else "LLM call failed")
        response.parsed = response.parsed or parse_json_object(response.content)
        response_payload = {"content": response.content, "parsed": response.parsed, "raw": response.raw}
        response_artifact = store.write_json(
            db,
            big_bang_id=big_bang_id,
            relative_path=f"big_bang_{big_bang_id}/sanitized_llm_calls/{purpose}_response.json",
            payload=redact_payload(response_payload),
            kind="llm_response_sanitized",
        )
        raw_response_artifact = store.write_json(
            db,
            big_bang_id=big_bang_id,
            relative_path=f"big_bang_{big_bang_id}/raw_llm_calls/{purpose}_response.json",
            payload=response_payload,
            kind="llm_response_raw",
            debug_only=True,
        )
        call.status = "succeeded"
        call.response_artifact_id = response_artifact.id
        call.meta = {
            **call.meta,
            "raw_response_artifact_id": str(raw_response_artifact.id),
            "attempts": attempts,
        }
        db.flush()
        return response, call
    except Exception as exc:
        fallback = LLMResponse(
            content=json.dumps({"error": str(exc), "fallback": True}),
            parsed={"error": str(exc), "fallback": True},
            raw={"error": str(exc)},
        )
        response_artifact = store.write_json(
            db,
            big_bang_id=big_bang_id,
            relative_path=f"big_bang_{big_bang_id}/sanitized_llm_calls/{purpose}_error.json",
            payload=redact_payload(fallback.model_dump()),
            kind="llm_response_sanitized",
        )
        call.status = "failed"
        call.response_artifact_id = response_artifact.id
        call.meta = {**call.meta, "error": str(exc), "attempts": attempts}
        db.flush()
        return fallback, call
