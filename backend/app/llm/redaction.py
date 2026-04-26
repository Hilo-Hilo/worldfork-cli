from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEY_PARTS = {
    "apikey",
    "accesstoken",
    "accesskey",
    "authorization",
    "bearer",
    "clientsecret",
    "credential",
    "jwt",
    "openrouterapikey",
    "password",
    "passwd",
    "privatekey",
    "secret",
    "sessionkey",
    "token",
}

INLINE_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\b(Bearer)\s+([A-Za-z0-9._~+/=-]{12,})", re.IGNORECASE),
    re.compile(r"\b(sk-(?:or-v1-)?[A-Za-z0-9_-]{16,})\b"),
    re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{16,})\b"),
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    re.compile(r"\b(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b"),
    re.compile(
        r"\b(api[_-]?key|access[_-]?token|auth(?:orization)?|client[_-]?secret|"
        r"password|secret|token)\s*[:=]\s*([\"']?)([^\"'\s,;]{8,})(\2)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<key>\"?(?:api[_-]?key|access[_-]?token|auth(?:orization)?|client[_-]?secret|"
        r"password|secret|token)\"?\s*[:=]\s*)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        re.IGNORECASE | re.DOTALL,
    ),
]


def _is_sensitive_key(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_text(value: str) -> str:
    redacted = value
    for pattern in INLINE_SECRET_PATTERNS:
        if "key" in pattern.groupindex:
            redacted = pattern.sub(_redact_quoted_secret, redacted)
        elif pattern.groups >= 4:
            redacted = pattern.sub(r"\1=\2[REDACTED]\4", redacted)
        elif pattern.groups == 2:
            redacted = pattern.sub(r"\1 [REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _redact_quoted_secret(match: re.Match) -> str:
    secret = match.group("value")
    if len(secret.strip()) < 8 and "\n" not in secret:
        return match.group(0)
    return f"{match.group('key')}{match.group('quote')}[REDACTED]{match.group('quote')}"


def redact_payload(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _is_sensitive_key(key) else redact_payload(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_payload(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value
