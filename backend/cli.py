#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx


DEFAULT_BASE_URL = (
    os.getenv("WORLD_FORK_API_BASE")
    or os.getenv("BACKEND_API_BASE")
    or "http://127.0.0.1:8003"
)
DEFAULT_API_PREFIX = "/api"
DEFAULT_TIMEOUT: float | None = None
DEFAULT_ENV_FILE = os.getenv("WORLD_FORK_ENV_FILE", ".env")


def _safe_json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def _is_json_text(value: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def _read_json_file(path: str | Path) -> dict[str, Any]:
    payload = Path(path).expanduser()
    if not payload.exists():
        raise FileNotFoundError(f"JSON file not found: {payload}")
    data = json.loads(payload.read_text())
    if not isinstance(data, dict):
        raise ValueError("payload file must contain a JSON object")
    return data


def _read_stdin_text() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read().strip()


def _print_table(items: list[dict[str, Any]], columns: list[str]) -> None:
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


def _short_id(value: Any, length: int = 12) -> str:
    return str(value)[:length]


def _format_run_status(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row.get("id") or row.get("big_bang_id") or row.get("run_id") or ""),
            "status": row.get("status", "unknown"),
            "name": row.get("name", row.get("display_name", "")),
            "created_at": row.get("created_at", ""),
        }
        for row in rows
    ]


class WorldForkClient:
    def __init__(self, base_url: str, api_prefix: str = DEFAULT_API_PREFIX, timeout: float | None = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.strip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _normalize_path(self, path: str) -> str:
        raw = path.strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        trimmed = raw.lstrip("/")
        if self.api_prefix and not trimmed.startswith(f"{self.api_prefix}/") and trimmed != self.api_prefix:
            return f"{self.api_prefix}/{trimmed}"
        return trimmed

    def request(self, method: str, path: str, *, json_body: Any = None, params: dict[str, Any] | None = None) -> Any:
        url = self._normalize_path(path)
        try:
            response = self._http.request(method, url, json=json_body, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message = exc.response.text
            raise RuntimeError(f"HTTP {exc.response.status_code} {exc.request.method} {url}: {message}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"request failed for {url}: {exc}") from exc

        if not response.text:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text


def _ensure_response(args: argparse.Namespace, data: Any, *, heading: str | None = None) -> None:
    if args.json:
        print(_safe_json_dump(data))
        return
    if heading:
        print(f"{heading}:")
    if isinstance(data, dict):
        print(_safe_json_dump(data))
    elif isinstance(data, list):
        if not data:
            print("(no results)")
        else:
            print(_safe_json_dump(data))
    else:
        print(data)


def cmd_status(args: argparse.Namespace, client: WorldForkClient) -> None:
    health = client.request("GET", "/health")
    big_bangs = client.request("GET", "/big-bangs")

    if not args.json:
        print("WorldFork backend: health")
        print(_safe_json_dump(health))
        print("")
        print(f"Configured API root: {urljoin(client.base_url + '/', client._normalize_path('/'))}")
        print(f"Observed big-bang count: {len(big_bangs)}")
        if isinstance(big_bangs, list):
            rows = _format_run_status(big_bangs)
            if rows:
                _print_table(rows[:50], ["id", "name", "status", "created_at"])
        return

    print(_safe_json_dump({"health": health, "big_bangs": big_bangs}))


def cmd_set_key(args: argparse.Namespace) -> None:
    env_file = Path(args.env_file).expanduser()
    if env_file.exists():
        lines = env_file.read_text().splitlines()
    else:
        lines = []

    rewritten = []
    updated = False
    key = args.key

    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            rewritten.append(line)
            continue

        raw_name, _, raw_value = line.partition("=")
        if raw_name.strip() == key:
            rewritten.append(f"{key}={args.value}")
            updated = True
        else:
            rewritten.append(line)

    if not updated:
        rewritten.append(f"{key}={args.value}")

    env_file.write_text("\n".join(rewritten).rstrip() + "\n")
    print(f"Updated {key} in {env_file}")


def cmd_bigbang_list(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", "/big-bangs")
    if args.json:
        _ensure_response(args, response)
        return

    rows = [
        {
            "id": str(item.get("id", "")),
            "status": item.get("status", ""),
            "name": item.get("name", ""),
            "created_at": item.get("created_at", ""),
        }
        for item in response
    ]
    if not rows:
        print("No Big Bangs found.")
        return
    _print_table(rows, ["id", "name", "status", "created_at"])


def cmd_bigbang_create(args: argparse.Namespace, client: WorldForkClient) -> None:
    payload: dict[str, Any] = {
        "name": args.name,
        "description": args.description,
    }
    if args.description is not None:
        payload["description"] = args.description

    if args.payload:
        payload.update(_read_json_file(args.payload))

    if args.scenario_text:
        payload["scenario_text"] = args.scenario_text
    else:
        stdin_text = _read_stdin_text()
        if stdin_text:
            payload["scenario_text"] = stdin_text

    response = client.request("POST", "/big-bangs", json_body=payload)
    _ensure_response(args, response)


def cmd_bigbang_action(args: argparse.Namespace, client: WorldForkClient, action: str) -> None:
    response = client.request("POST", f"/big-bangs/{args.big_bang_id}/{action}")
    _ensure_response(args, response)


def cmd_bigbang_run_until_complete(args: argparse.Namespace, client: WorldForkClient) -> None:
    body: dict[str, Any] = {}
    if args.max_ticks:
        body["max_total_ticks"] = args.max_ticks

    if not args.sync:
        job_payload: dict[str, Any] = {
            "job_type": "run_big_bang_until_complete",
            "big_bang_id": args.big_bang_id,
            "payload": body,
        }
        response = client.request("POST", "/jobs", json_body=job_payload)
        if not args.json:
            job_id = response.get("id") or response.get("job_id") if isinstance(response, dict) else None
            print(f"Queued run_big_bang_until_complete for {args.big_bang_id}.")
            if job_id:
                print(f"  job_id: {job_id}")
            print("  Track with: jobs list / logs errors / multiverse metrics")
            print("  Use --sync to block on the simulation instead (long).")
        else:
            print(_safe_json_dump(response))
        return

    print(
        "WARNING: --sync runs the entire simulation in the API request thread.\n"
        f"  This will block the CLI until {args.max_ticks} tick(s) finish across all active universes.\n"
        "  Wall time depends on:\n"
        "    - --max-ticks (current: %d)\n"
        "    - DEFAULT_MODEL / FALLBACK_MODEL set in .env (LLM latency dominates)\n"
        "    - active universe count and branching\n"
        "  Expect tens of minutes to hours for non-trivial scenarios.\n"
        "  Bump --timeout (default 120s) accordingly, e.g. --timeout 7200."
        % args.max_ticks,
        file=sys.stderr,
    )
    response = client.request(
        "POST", f"/big-bangs/{args.big_bang_id}/run-until-complete", json_body=body or None
    )
    _ensure_response(args, response)


def cmd_bigbang_reports(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/big-bangs/{args.big_bang_id}/reports")
    if args.json:
        _ensure_response(args, response)
        return

    if not response:
        print("No reports yet.")
        return

    rows = [
        {
            "id": str(item.get("id", "")),
            "version": item.get("version", ""),
            "title": item.get("title", ""),
            "summary": (item.get("summary", "") or "")[:120],
        }
        for item in response
    ]
    _print_table(rows, ["id", "version", "title", "summary"])


def cmd_bigbang_final_report(args: argparse.Namespace, client: WorldForkClient) -> None:
    body: dict[str, Any] = {}
    if args.title:
        body["title"] = args.title
    if args.summary:
        body["summary"] = args.summary

    response = client.request(
        "POST",
        f"/big-bangs/{args.big_bang_id}/reports/final",
        json_body=body or None,
    )
    _ensure_response(args, response)


def cmd_run_list(args: argparse.Namespace, client: WorldForkClient) -> None:
    params: dict[str, Any] = {}
    if args.status:
        params["status"] = args.status
    if args.q:
        params["q"] = args.q
    if args.limit:
        params["limit"] = args.limit

    response = client.request("GET", "/runs", params=params)
    _ensure_response(args, response)


def cmd_jobs_types(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", "/jobs/types")
    _ensure_response(args, response)


def cmd_jobs_list(args: argparse.Namespace, client: WorldForkClient) -> None:
    params = {"limit": args.limit}
    if args.big_bang_id:
        params["big_bang_id"] = args.big_bang_id
    response = client.request("GET", "/jobs", params=params)
    if args.json:
        _ensure_response(args, response)
        return

    rows = [
        {
            "id": str(item.get("id", "")),
            "type": item.get("job_type", ""),
            "status": item.get("status", ""),
            "run": str(item.get("run_id", "") or item.get("big_bang_id", "")),
            "created": item.get("created_at", ""),
        }
        for item in response
    ]
    if not rows:
        print("No jobs found.")
        return
    _print_table(rows, ["id", "type", "status", "run", "created"])


def cmd_jobs_create(args: argparse.Namespace, client: WorldForkClient) -> None:
    payload: dict[str, Any] = {
        "job_type": args.job_type,
        "payload": _is_json_text(args.payload),
        "idempotency_key": args.idempotency_key,
    }
    if args.big_bang_id:
        payload["big_bang_id"] = args.big_bang_id

    response = client.request("POST", "/jobs", json_body=payload)
    _ensure_response(args, response)

def cmd_jobs_run(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("POST", f"/jobs/{args.job_id}/run")
    _ensure_response(args, response)


def cmd_multiverse_dag(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/multiverse/{args.big_bang_id}/dag")
    if args.json:
        _ensure_response(args, response)
        return

    nodes = response.get("nodes", []) if isinstance(response, dict) else []
    edges = response.get("edges", []) if isinstance(response, dict) else []
    node_map = {str(item.get("universe_id")): item for item in nodes}
    children = defaultdict(list)
    for edge in edges:
        src = str(edge.get("source", ""))
        dst = str(edge.get("target", ""))
        if src and dst:
            children[src].append(dst)

    for source in children.values():
        source.sort()

    def label(node_id: str) -> str:
        node = node_map.get(node_id, {})
        base = _short_id(node_id)
        status = node.get("status", "unknown")
        return f"{base} [{status}]"

    def render_tree(node_id: str, prefix: str = "", seen: set[str] | None = None) -> None:
        if seen is None:
            seen = set()
        if node_id in seen:
            print(prefix + f"{label(node_id)} (cycle)")
            return
        seen.add(node_id)
        print(prefix + label(node_id))
        for child in children.get(node_id, []):
            render_tree(child, prefix + "  ", seen)

    all_node_ids = set(node_map)
    roots = sorted(
        [node_id for node_id, node in node_map.items() if not node.get("parent_multiverse_id")]
    )

    if not roots and all_node_ids:
        roots = sorted(all_node_ids)

    if not all_node_ids:
        print("No graph nodes found for this Big Bang.")
        return

    print(f"Multiverse DAG for Big Bang {_short_id(args.big_bang_id)}")
    print(f"Total universes: {len(nodes)}")
    for root in roots:
        render_tree(root)

    print("\nAdjacency edges:")
    for node in nodes:
        src = str(node.get("universe_id"))
        if children.get(src):
            print(f"  {label(src)} -> {', '.join(_short_id(c) for c in children[src])}")


def cmd_multiverse_metrics(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/multiverse/{args.big_bang_id}/metrics")
    _ensure_response(args, response)


def cmd_multiverse_step(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("POST", f"/multiverse/{args.big_bang_id}/simulate-next-tick")
    _ensure_response(args, response)


def cmd_multiverse_tree(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/multiverse/{args.big_bang_id}/tree")
    _ensure_response(args, response)


def cmd_universe_step(args: argparse.Namespace, client: WorldForkClient) -> None:
    body: dict[str, Any] = {}
    if args.tick is not None:
        body["tick"] = args.tick
    response = client.request(
        "POST",
        f"/universes/{args.universe_id}/step",
        json_body=body or None,
    )
    _ensure_response(args, response)


def cmd_universe_force_deviation(args: argparse.Namespace, client: WorldForkClient) -> None:
    body: dict[str, Any] = {
        "tick": args.tick,
        "mode": args.mode,
        "reason": args.reason,
        "auto_start": args.auto_start,
    }

    if args.mode == "god_prompt":
        if args.prompt:
            body["prompt"] = args.prompt
        elif args.prompt_file:
            body["prompt"] = Path(args.prompt_file).read_text().strip()
        else:
            raise RuntimeError("--prompt or --prompt-file is required for god_prompt mode")
    elif args.mode == "structured_delta":
        if not args.delta and not args.delta_file:
            raise RuntimeError("--delta or --delta-file is required for structured_delta mode")
        if args.delta:
            body["delta"] = _is_json_text(args.delta)
        else:
            body["delta"] = _read_json_file(args.delta_file)

    response = client.request("POST", f"/universes/{args.universe_id}/force-deviation", json_body=body)
    _ensure_response(args, response)


def cmd_universe_trace(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request(
        "GET",
        f"/universes/{args.universe_id}/ticks/{args.tick}/trace",
        params={"include_raw": args.include_raw},
    )
    _ensure_response(args, response)


def cmd_logs_list(args: argparse.Namespace, client: WorldForkClient, scope: str) -> None:
    path = "/logs/" + scope
    params: dict[str, Any] = {"limit": args.limit, "offset": args.offset}
    for key in ("run_id", "universe_id", "provider", "status"):
        value = getattr(args, key, None)
        if value:
            params[key] = value

    response = client.request("GET", path, params=params)
    if args.json:
        _ensure_response(args, response)
        return

    if scope == "errors":
        if not response:
            print("No error logs.")
            return
        for item in response:
            print(f"[{item.get('source', 'error')}] {item.get('status')} {item.get('error')}")
            print(f"  id: {item.get('id')} | run: {_short_id(item.get('run_id', ''))}")
            print()
        return

    _ensure_response(args, response)


def cmd_search(args: argparse.Namespace) -> None:
    query = args.query.strip()
    if not query:
        raise RuntimeError("search query is required")

    transport = httpx.Client(timeout=args.timeout)
    response = transport.get(
        "https://duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "WorldFork-CLI/1.0"},
    )
    response.raise_for_status()
    text = response.text
    matches = re.findall(
        r'<a[^>]+class="[^\"]*result__a[^\"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        text,
    )

    parsed = []
    for url, title in matches[:args.limit]:
        parsed.append({
            "url": html.unescape(url),
            "title": re.sub(r"<[^>]+>", "", html.unescape(title)).strip(),
        })

    if not parsed:
        print("No search results.")
        return

    if args.json:
        print(_safe_json_dump(parsed))
        return

    for row in parsed:
        print(f"- {row['title'] or row['url']}\n  {row['url']}")


def cmd_troubleshoot(args: argparse.Namespace, client: WorldForkClient) -> None:
    health = client.request("GET", "/health")
    errors = client.request("GET", "/logs/errors", params={"limit": args.limit})
    jobs = client.request("GET", "/jobs") if args.include_jobs else None

    report = {
        "health": health,
        "error_count": len(errors) if isinstance(errors, list) else 0,
        "errors": errors,
    }
    if isinstance(jobs, list):
        report["recent_jobs_count"] = len(jobs)
        report["recent_jobs"] = jobs[: min(5, len(jobs))]

    if args.json:
        _ensure_response(args, report)
        return

    print("Troubleshoot summary:")
    print(_safe_json_dump({"health": health, "error_count": report["error_count"], "recent_jobs_count": report.get("recent_jobs_count", 0)}))
    if not errors:
        print("No logged errors detected.")


def cmd_query(args: argparse.Namespace, client: WorldForkClient) -> None:
    payload = _is_json_text(args.data) if args.data else None
    if args.payload_file:
        payload = _read_json_file(args.payload_file)
    response = client.request(args.method.upper(), args.path, json_body=payload)
    _ensure_response(args, response)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WorldFork backend CLI")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the backend")
    parser.add_argument("--api-prefix", default=DEFAULT_API_PREFIX, help="API prefix (default: /api)")
    parser.add_argument(
        "--timeout",
        default=DEFAULT_TIMEOUT,
        type=float,
        help="HTTP timeout seconds (default: none — wait indefinitely; pass a number to cap)",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON responses")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="Environment file path for set-key")

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_status = subparsers.add_parser("status", help="Get API health and current Big Bang count")
    parser_status.set_defaults(func=lambda a, c: cmd_status(a, c))

    parser_set_key = subparsers.add_parser("set-key", help="Write API key values to an env file")
    parser_set_key.add_argument("key", help="Environment variable name")
    parser_set_key.add_argument("value", help="Raw key value")
    parser_set_key.set_defaults(func=lambda a, c: cmd_set_key(a))

    query_parser = subparsers.add_parser("query", help="Run an arbitrary API request")
    query_parser.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    query_parser.add_argument("path", help="API path, e.g. /api/big-bangs")
    query_parser.add_argument("--data", help="JSON string payload")
    query_parser.add_argument("--payload-file", help="Path to a JSON payload file")
    query_parser.set_defaults(func=cmd_query)

    parser_search = subparsers.add_parser("search", help="Search the web for context references")
    parser_search.add_argument("query", help="Search query")
    parser_search.add_argument("--limit", type=int, default=6)
    parser_search.set_defaults(func=lambda a, c: cmd_search(a))

    parser_trouble = subparsers.add_parser("troubleshoot", help="Gather health + error context")
    parser_trouble.add_argument("--run-id", dest="run_id", help="Optional run id filter")
    parser_trouble.add_argument("--limit", type=int, default=50)
    parser_trouble.add_argument("--include-jobs", action="store_true")
    parser_trouble.set_defaults(func=cmd_troubleshoot)

    bigbang = subparsers.add_parser("bigbang", help="Manage Big Bang runs")
    bb_sub = bigbang.add_subparsers(dest="bigbang_command", required=True)

    bb_list = bb_sub.add_parser("list", help="List Big Bangs")
    bb_list.set_defaults(func=cmd_bigbang_list)

    bb_create = bb_sub.add_parser("create", help="Create a Big Bang")
    bb_create.add_argument("name")
    bb_create.add_argument("--description")
    bb_create.add_argument("--scenario-text", help="Scenario text inline")
    bb_create.add_argument("--payload", help="Path to JSON object payload")
    bb_create.set_defaults(func=cmd_bigbang_create)

    bb_start = bb_sub.add_parser("start", help="Start a Big Bang")
    bb_start.add_argument("big_bang_id")
    bb_start.set_defaults(func=lambda a, c: cmd_bigbang_action(a, c, "start"))

    bb_pause = bb_sub.add_parser("pause", help="Pause a Big Bang")
    bb_pause.add_argument("big_bang_id")
    bb_pause.set_defaults(func=lambda a, c: cmd_bigbang_action(a, c, "pause"))

    bb_resume = bb_sub.add_parser("resume", help="Resume a Big Bang")
    bb_resume.add_argument("big_bang_id")
    bb_resume.set_defaults(func=lambda a, c: cmd_bigbang_action(a, c, "resume"))

    bb_run_complete = bb_sub.add_parser(
        "run-until-complete",
        help="Run a Big Bang to completion (default: enqueue async job; --sync blocks the CLI)",
    )
    bb_run_complete.add_argument("big_bang_id")
    bb_run_complete.add_argument("--max-ticks", type=int, default=24)
    bb_run_complete.add_argument(
        "--sync",
        action="store_true",
        help="Block the CLI on the API call until the simulation finishes (slow; bump --timeout).",
    )
    bb_run_complete.set_defaults(func=cmd_bigbang_run_until_complete)

    bb_reports = bb_sub.add_parser("reports", help="List reports for a Big Bang")
    bb_reports.add_argument("big_bang_id")
    bb_reports.set_defaults(func=cmd_bigbang_reports)

    bb_final = bb_sub.add_parser("final-report", help="Generate the final report")
    bb_final.add_argument("big_bang_id")
    bb_final.add_argument("--title")
    bb_final.add_argument("--summary")
    bb_final.set_defaults(func=cmd_bigbang_final_report)

    runs = subparsers.add_parser("runs", help="List run metadata")
    runs.add_argument("--status")
    runs.add_argument("--q")
    runs.add_argument("--limit", type=int, default=50)
    runs.set_defaults(func=cmd_run_list)

    multiverse = subparsers.add_parser("multiverse", help="Dependency graph and tick controls")
    mv_sub = multiverse.add_subparsers(dest="multiverse_command", required=True)

    mv_tree = mv_sub.add_parser("tree", help="Get run dependency snapshot")
    mv_tree.add_argument("big_bang_id")
    mv_tree.set_defaults(func=cmd_multiverse_tree)

    mv_dag = mv_sub.add_parser("dag", help="Print multiverse dependency DAG")
    mv_dag.add_argument("big_bang_id")
    mv_dag.set_defaults(func=cmd_multiverse_dag)

    mv_metrics = mv_sub.add_parser("metrics", help="Get multiverse aggregate metrics")
    mv_metrics.add_argument("big_bang_id")
    mv_metrics.set_defaults(func=cmd_multiverse_metrics)

    mv_step = mv_sub.add_parser("step", help="Queue one tick across active universes")
    mv_step.add_argument("big_bang_id")
    mv_step.set_defaults(func=cmd_multiverse_step)

    universe = subparsers.add_parser("universe", help="Universe-level interventions")
    uni_sub = universe.add_subparsers(dest="universe_command", required=True)

    uni_step = uni_sub.add_parser("step", help="Simulate a single universe tick")
    uni_step.add_argument("universe_id")
    uni_step.add_argument("--tick", type=int)
    uni_step.set_defaults(func=cmd_universe_step)

    uni_force = uni_sub.add_parser("force-deviation", help="Force manual intervention")
    uni_force.add_argument("universe_id")
    uni_force.add_argument("tick", type=int)
    uni_force.add_argument("--mode", choices=["god_prompt", "structured_delta"], default="god_prompt")
    uni_force.add_argument("--reason", default="")
    uni_force.add_argument("--prompt")
    uni_force.add_argument("--prompt-file")
    uni_force.add_argument("--delta", help="Structured delta JSON string")
    uni_force.add_argument("--delta-file", help="Structured delta JSON file")
    uni_force.add_argument("--no-auto-start", dest="auto_start", action="store_false")
    uni_force.set_defaults(func=cmd_universe_force_deviation)

    uni_trace = uni_sub.add_parser("trace", help="Pull trace for a universe tick")
    uni_trace.add_argument("universe_id")
    uni_trace.add_argument("tick", type=int)
    uni_trace.add_argument("--include-raw", action="store_true")
    uni_trace.set_defaults(func=cmd_universe_trace)

    jobs = subparsers.add_parser("jobs", help="Inspect background jobs")
    jobs_sub = jobs.add_subparsers(dest="jobs_command", required=True)

    jobs_types = jobs_sub.add_parser("types")
    jobs_types.set_defaults(func=cmd_jobs_types)

    jobs_list = jobs_sub.add_parser("list")
    jobs_list.add_argument("--big-bang-id")
    jobs_list.add_argument("--limit", type=int, default=100)
    jobs_list.set_defaults(func=cmd_jobs_list)

    jobs_create = jobs_sub.add_parser("create")
    jobs_create.add_argument("job_type")
    jobs_create.add_argument("--big-bang-id")
    jobs_create.add_argument("--payload", required=True)
    jobs_create.add_argument("--idempotency-key")
    jobs_create.set_defaults(func=cmd_jobs_create)

    jobs_run = jobs_sub.add_parser("run")
    jobs_run.add_argument("job_id")
    jobs_run.set_defaults(func=cmd_jobs_run)

    logs = subparsers.add_parser("logs", help="Inspect API and job logs")
    logs_sub = logs.add_subparsers(dest="logs_command", required=True)

    logs_requests = logs_sub.add_parser("requests")
    logs_requests.add_argument("--run-id")
    logs_requests.add_argument("--universe-id")
    logs_requests.add_argument("--provider")
    logs_requests.add_argument("--status")
    logs_requests.add_argument("--limit", type=int, default=100)
    logs_requests.add_argument("--offset", type=int, default=0)
    logs_requests.set_defaults(func=lambda a, c: cmd_logs_list(a, c, "requests"))

    logs_errors = logs_sub.add_parser("errors")
    logs_errors.add_argument("--run-id")
    logs_errors.add_argument("--limit", type=int, default=100)
    logs_errors.add_argument("--offset", type=int, default=0)
    logs_errors.set_defaults(func=lambda a, c: cmd_logs_list(a, c, "errors"))

    logs_webhooks = logs_sub.add_parser("webhooks")
    logs_webhooks.add_argument("--run-id")
    logs_webhooks.add_argument("--status")
    logs_webhooks.add_argument("--limit", type=int, default=100)
    logs_webhooks.add_argument("--offset", type=int, default=0)
    logs_webhooks.set_defaults(func=lambda a, c: cmd_logs_list(a, c, "webhooks"))

    logs_audit = logs_sub.add_parser("audit")
    logs_audit.add_argument("--limit", type=int, default=100)
    logs_audit.add_argument("--offset", type=int, default=0)
    logs_audit.set_defaults(func=lambda a, c: cmd_logs_list(a, c, "audit"))

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    client = WorldForkClient(args.base_url, api_prefix=args.api_prefix, timeout=args.timeout)

    if args.command != "set-key" and args.command != "search":
        if not args.base_url:
            raise RuntimeError("--base-url is required")

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        raise SystemExit(2)

    try:
        func(args, client)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
