from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def safe_json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def parse_json_text(value: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def read_json_file(path: str | Path) -> dict[str, Any]:
    payload = Path(path).expanduser()
    if not payload.exists():
        raise FileNotFoundError(f"JSON file not found: {payload}")
    data = json.loads(payload.read_text())
    if not isinstance(data, dict):
        raise ValueError("payload file must contain a JSON object")
    return data


def read_stdin_text() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def print_table(items: list[dict[str, Any]], columns: list[str]) -> None:
    widths = [len(col) for col in columns]
    for row in items:
        for idx, col in enumerate(columns):
            text = str(row.get(col, ""))
            widths[idx] = max(widths[idx], len(text))

    header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
    print(header)
    print("-+-".join("-" * width for width in widths))
    for row in items:
        row_text = [str(row.get(col, "")) for col in columns]
        print(" | ".join(row_text[i].ljust(widths[i]) for i in range(len(columns))))


def short_id(value: Any, length: int = 12) -> str:
    """Truncated identifier for tree/DAG visualization only.

    Never use this for table 'id' columns — users need full IDs to chain
    commands. ULIDs share long timestamp prefixes, so 12 chars is the
    minimum that lets close-in-time IDs visually diverge.
    """
    return str(value)[:length]


def emit(args: argparse.Namespace, data: Any, *, heading: str | None = None) -> None:
    if args.json:
        print(safe_json_dump(data))
        return
    if heading:
        print(f"{heading}:")
    if isinstance(data, dict):
        print(safe_json_dump(data))
    elif isinstance(data, list):
        if not data:
            print("(no results)")
        else:
            print(safe_json_dump(data))
    else:
        print(data)


def format_run_status(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row.get("id") or row.get("big_bang_id") or row.get("run_id") or ""),
            "status": row.get("status", "unknown"),
            "name": row.get("name", row.get("display_name", "")),
            "created_at": row.get("created_at", ""),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Verbosity / projection
# ---------------------------------------------------------------------------
#
# All filtering happens client-side. The backend has no field-projection or
# verbosity knob (confirmed against openapi). We pull the full payload and
# project it into a smaller dict before display, so an LLM agent can ask for
# `summary` or `--fields actor_id,rationale` without overflowing context.

VERBOSITY_TIERS = ("summary", "normal", "full")
DEFAULT_VERBOSITY = "normal"

# Per-surface key allowlists. "full" means "no projection — keep everything".
# Order matters for table output where applicable.
VERBOSITY_SCHEMAS: dict[str, dict[str, list[str] | None]] = {
    "universe_trace_actor": {
        "summary": ["actor_id", "actor_kind", "job_type"],
        "normal": [
            "actor_id",
            "actor_kind",
            "job_type",
            "rationale",
            "self_ratings",
            "state_delta",
        ],
        "full": None,
    },
    "universe_trace_envelope": {
        # Envelope keys kept around the (already-projected) actors array.
        "summary": ["universe_id", "tick", "actor_count"],
        "normal": [
            "universe_id",
            "tick",
            "actors",
            "god_decision",
            "state_delta",
        ],
        "full": None,
    },
    "logs_requests_row": {
        "summary": ["call_id", "job_type", "status", "total_tokens", "latency_ms"],
        "normal": [
            "call_id",
            "job_type",
            "status",
            "total_tokens",
            "latency_ms",
            "provider",
            "model_used",
            "run_id",
            "universe_id",
            "tick",
        ],
        "full": None,
    },
    "logs_errors_row": {
        "summary": ["id", "status", "error"],
        "normal": ["id", "status", "error", "run_id", "universe_id", "tick", "source"],
        "full": None,
    },
    "logs_audit_row": {
        "summary": ["id", "action", "timestamp"],
        "normal": ["id", "action", "timestamp", "resource", "actor", "details"],
        "full": None,
    },
    "logs_webhooks_row": {
        "summary": ["id", "status", "timestamp"],
        "normal": ["id", "status", "timestamp", "resource", "run_id"],
        "full": None,
    },
    "cohort_transcript_row": {
        "summary": ["tick", "rationale"],
        "normal": ["tick", "rationale", "self_ratings", "state_delta"],
        "full": None,
    },
}


def parse_fields(value: str | None) -> list[str] | None:
    """Parse a ``--fields a,b,c`` argument into a key list, or ``None`` for no override."""
    if not value:
        return None
    keys = [k.strip() for k in value.split(",") if k.strip()]
    return keys or None


def project(obj: dict[str, Any], keys: list[str] | None) -> dict[str, Any]:
    """Return a new dict containing only ``keys`` that exist in ``obj``.

    ``keys=None`` means "no projection" — return ``obj`` unchanged. Missing
    keys are silently skipped so projection never raises on partial responses.
    """
    if keys is None:
        return obj
    return {k: obj[k] for k in keys if k in obj}


def project_list(items: list[dict[str, Any]], keys: list[str] | None) -> list[dict[str, Any]]:
    if keys is None:
        return items
    return [project(item, keys) for item in items]


def resolve_verbosity_keys(
    surface: str,
    tier: str,
    fields: list[str] | None,
) -> list[str] | None:
    """Decide which key list to project ``surface`` against.

    Precedence: explicit ``--fields`` wins; otherwise the schema entry for
    ``tier``; ``full`` (or an unknown surface) means no projection.
    """
    if fields is not None:
        return fields
    schema = VERBOSITY_SCHEMAS.get(surface)
    if schema is None:
        return None
    return schema.get(tier)


def truncate(value: Any, limit: int) -> Any:
    """Truncate strings; pass through everything else. Used by handlers that
    want to bound a single field (e.g. ``error`` text in summary mode)."""
    if isinstance(value, str) and len(value) > limit:
        return value[: limit - 1] + "…"
    return value
