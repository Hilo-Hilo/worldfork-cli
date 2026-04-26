from __future__ import annotations

SENSITIVE_KEYS = {"api_key", "authorization", "token", "secret"}


def redact_payload(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if key.lower() in SENSITIVE_KEYS else redact_payload(val) for key, val in value.items()}
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value
