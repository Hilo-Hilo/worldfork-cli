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
