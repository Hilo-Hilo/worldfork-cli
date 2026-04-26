from __future__ import annotations

import argparse
import html
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from worldfork.client import WorldForkClient
from worldfork.output import (
    emit,
    format_run_status,
    parse_fields,
    parse_json_text,
    print_table,
    project,
    project_list,
    read_json_file,
    read_stdin_text,
    resolve_verbosity_keys,
    safe_json_dump,
    short_id,
    truncate,
)

# ---------------------------------------------------------------------------
# status / troubleshoot
# ---------------------------------------------------------------------------

def status(args: argparse.Namespace, client: WorldForkClient) -> None:
    health = client.request("GET", "/health")
    big_bangs = client.request("GET", "/big-bangs")

    if not args.json:
        print("WorldFork backend: health")
        print(safe_json_dump(health))
        print("")
        api_root = urljoin(client.base_url + "/", client.normalize_path("/"))
        print(f"Configured API root: {api_root}")
        if isinstance(big_bangs, list):
            print(f"Observed big-bang count: {len(big_bangs)}")
            rows = format_run_status(big_bangs)
            if rows:
                print_table(rows[:50], ["id", "name", "status", "created_at"])
        else:
            print(f"big-bangs response: {type(big_bangs).__name__}")
        return

    print(safe_json_dump({"health": health, "big_bangs": big_bangs}))


def troubleshoot(args: argparse.Namespace, client: WorldForkClient) -> None:
    health = client.request("GET", "/health")
    errors = client.request("GET", "/logs/errors", params={"limit": args.limit})
    jobs = client.request("GET", "/jobs") if args.include_jobs else None

    report: dict[str, Any] = {
        "health": health,
        "error_count": len(errors) if isinstance(errors, list) else 0,
        "errors": errors,
    }
    if isinstance(jobs, list):
        report["recent_jobs_count"] = len(jobs)
        report["recent_jobs"] = jobs[: min(5, len(jobs))]

    if args.json:
        emit(args, report)
        return

    print("Troubleshoot summary:")
    print(
        safe_json_dump(
            {
                "health": health,
                "error_count": report["error_count"],
                "recent_jobs_count": report.get("recent_jobs_count", 0),
            }
        )
    )
    if not errors:
        print("No logged errors detected.")


# ---------------------------------------------------------------------------
# set-key (writes to local .env, no API call)
# ---------------------------------------------------------------------------

def set_key(args: argparse.Namespace) -> None:
    env_file = Path(args.env_file).expanduser()
    lines = env_file.read_text().splitlines() if env_file.exists() else []

    rewritten: list[str] = []
    updated = False

    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            rewritten.append(line)
            continue
        raw_name, _, _ = line.partition("=")
        if raw_name.strip() == args.key:
            rewritten.append(f"{args.key}={args.value}")
            updated = True
        else:
            rewritten.append(line)

    if not updated:
        rewritten.append(f"{args.key}={args.value}")

    env_file.write_text("\n".join(rewritten).rstrip() + "\n")
    print(f"Updated {args.key} in {env_file}")


# ---------------------------------------------------------------------------
# query / search
# ---------------------------------------------------------------------------

def query(args: argparse.Namespace, client: WorldForkClient) -> None:
    payload = parse_json_text(args.data) if args.data else None
    if args.payload_file:
        payload = read_json_file(args.payload_file)
    response = client.request(args.method.upper(), args.path, json_body=payload)
    emit(args, response)


def search(args: argparse.Namespace) -> None:
    query_text = args.query.strip()
    if not query_text:
        raise RuntimeError("search query is required")

    transport = httpx.Client(timeout=args.timeout)
    response = transport.get(
        "https://duckduckgo.com/html/",
        params={"q": query_text},
        headers={"User-Agent": "WorldFork-CLI/1.0"},
    )
    response.raise_for_status()
    matches = re.findall(
        r'<a[^>]+class="[^\"]*result__a[^\"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        response.text,
    )

    parsed: list[dict[str, str]] = []
    for url, title in matches[: args.limit]:
        parsed.append(
            {
                "url": html.unescape(url),
                "title": re.sub(r"<[^>]+>", "", html.unescape(title)).strip(),
            }
        )

    if not parsed:
        print("No search results.")
        return

    if args.json:
        print(safe_json_dump(parsed))
        return

    for row in parsed:
        print(f"- {row['title'] or row['url']}\n  {row['url']}")


# ---------------------------------------------------------------------------
# bigbang
# ---------------------------------------------------------------------------

def bigbang_list(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", "/big-bangs")
    if args.json:
        emit(args, response)
        return

    if not isinstance(response, list):
        emit(args, response)
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
    print_table(rows, ["id", "name", "status", "created_at"])


def bigbang_create(args: argparse.Namespace, client: WorldForkClient) -> None:
    payload: dict[str, Any] = {"name": args.name}
    if args.description is not None:
        payload["description"] = args.description
    if args.payload:
        payload.update(read_json_file(args.payload))
    if args.scenario_text:
        payload["scenario_text"] = args.scenario_text
    else:
        stdin_text = read_stdin_text()
        if stdin_text:
            payload["scenario_text"] = stdin_text
    response = client.request("POST", "/big-bangs", json_body=payload)
    emit(args, response)


def bigbang_action(args: argparse.Namespace, client: WorldForkClient, action: str) -> None:
    response = client.request("POST", f"/big-bangs/{args.big_bang_id}/{action}")
    emit(args, response)


def bigbang_run_until_complete(args: argparse.Namespace, client: WorldForkClient) -> None:
    body: dict[str, Any] = {}
    if args.max_ticks:
        body["max_total_ticks"] = args.max_ticks

    if not args.sync:
        job_payload = {
            "job_type": "run_big_bang_until_complete",
            "big_bang_id": args.big_bang_id,
            "payload": body,
        }
        response = client.request("POST", "/jobs", json_body=job_payload)
        if args.json:
            print(safe_json_dump(response))
            return
        job_id = (
            response.get("id") or response.get("job_id")
            if isinstance(response, dict)
            else None
        )
        print(f"Queued run_big_bang_until_complete for {args.big_bang_id}.")
        if job_id:
            print(f"  job_id: {job_id}")
        print("  Track with: worldfork jobs list / logs errors / multiverse metrics")
        print("  Use --sync to block on the simulation instead (long).")
        return

    print(
        "WARNING: --sync runs the entire simulation in the API request thread.\n"
        f"  This will block the CLI until {args.max_ticks} tick(s) finish across all active universes.\n"
        "  Wall time depends on:\n"
        f"    - --max-ticks (current: {args.max_ticks})\n"
        "    - DEFAULT_MODEL / FALLBACK_MODEL set on the server (LLM latency dominates)\n"
        "    - active universe count and branching\n"
        "  Expect tens of minutes to hours for non-trivial scenarios.\n"
        "  Bump --timeout if you want a hard cap, e.g. --timeout 7200.",
        file=sys.stderr,
    )
    response = client.request(
        "POST",
        f"/big-bangs/{args.big_bang_id}/run-until-complete",
        json_body=body or None,
    )
    emit(args, response)


def bigbang_reports(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/big-bangs/{args.big_bang_id}/reports")
    if args.json:
        emit(args, response)
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
    print_table(rows, ["id", "version", "title", "summary"])


def bigbang_final_report(args: argparse.Namespace, client: WorldForkClient) -> None:
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
    emit(args, response)


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------

def run_list(args: argparse.Namespace, client: WorldForkClient) -> None:
    params: dict[str, Any] = {}
    if args.status:
        params["status"] = args.status
    if args.q:
        params["q"] = args.q
    if args.limit:
        params["limit"] = args.limit
    response = client.request("GET", "/runs", params=params)
    emit(args, response)


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------

def jobs_types(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", "/jobs/types")
    emit(args, response)


def jobs_list(args: argparse.Namespace, client: WorldForkClient) -> None:
    params: dict[str, Any] = {"limit": args.limit}
    if args.big_bang_id:
        params["big_bang_id"] = args.big_bang_id
    response = client.request("GET", "/jobs", params=params)
    if args.json:
        emit(args, response)
        return
    if not isinstance(response, list):
        emit(args, response)
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
    print_table(rows, ["id", "type", "status", "run", "created"])


def jobs_create(args: argparse.Namespace, client: WorldForkClient) -> None:
    payload: dict[str, Any] = {
        "job_type": args.job_type,
        "payload": parse_json_text(args.payload),
        "idempotency_key": args.idempotency_key,
    }
    if args.big_bang_id:
        payload["big_bang_id"] = args.big_bang_id
    response = client.request("POST", "/jobs", json_body=payload)
    emit(args, response)


def jobs_run(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("POST", f"/jobs/{args.job_id}/run")
    emit(args, response)


# ---------------------------------------------------------------------------
# multiverse
# ---------------------------------------------------------------------------

def multiverse_dag(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/multiverse/{args.big_bang_id}/dag")
    if args.json:
        emit(args, response)
        return

    nodes = response.get("nodes", []) if isinstance(response, dict) else []
    edges = response.get("edges", []) if isinstance(response, dict) else []
    node_map = {str(item.get("universe_id")): item for item in nodes}
    children: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = str(edge.get("source", ""))
        dst = str(edge.get("target", ""))
        if src and dst:
            children[src].append(dst)
    for source in children.values():
        source.sort()

    def label(node_id: str) -> str:
        node = node_map.get(node_id, {})
        return f"{short_id(node_id)} [{node.get('status', 'unknown')}]"

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
        node_id
        for node_id, node in node_map.items()
        if not node.get("parent_multiverse_id")
    )
    if not roots and all_node_ids:
        roots = sorted(all_node_ids)
    if not all_node_ids:
        print("No graph nodes found for this Big Bang.")
        return

    print(f"Multiverse DAG for Big Bang {short_id(args.big_bang_id)}")
    print(f"Total universes: {len(nodes)}")
    for root in roots:
        render_tree(root)

    print("\nAdjacency edges:")
    for node in nodes:
        src = str(node.get("universe_id"))
        if children.get(src):
            print(
                f"  {label(src)} -> "
                f"{', '.join(short_id(c) for c in children[src])}"
            )


def multiverse_metrics(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/multiverse/{args.big_bang_id}/metrics")
    emit(args, response)


def multiverse_step(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request(
        "POST", f"/multiverse/{args.big_bang_id}/simulate-next-tick"
    )
    emit(args, response)


def multiverse_tree(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = client.request("GET", f"/multiverse/{args.big_bang_id}/tree")
    emit(args, response)


# ---------------------------------------------------------------------------
# universe
# ---------------------------------------------------------------------------

def universe_step(args: argparse.Namespace, client: WorldForkClient) -> None:
    body: dict[str, Any] = {}
    if args.tick is not None:
        body["tick"] = args.tick
    response = client.request(
        "POST", f"/universes/{args.universe_id}/step", json_body=body or None
    )
    emit(args, response)


def universe_force_deviation(args: argparse.Namespace, client: WorldForkClient) -> None:
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
            body["delta"] = parse_json_text(args.delta)
        else:
            body["delta"] = read_json_file(args.delta_file)
    response = client.request(
        "POST", f"/universes/{args.universe_id}/force-deviation", json_body=body
    )
    emit(args, response)


def _fetch_universe_trace(
    client: WorldForkClient,
    universe_id: str,
    tick: int,
    include_raw: bool,
) -> dict[str, Any]:
    """Fetch the raw trace payload. Shared between trace, actors, and cohort transcript."""
    return client.request(
        "GET",
        f"/universes/{universe_id}/ticks/{tick}/trace",
        params={"include_raw": include_raw},
    )


def _filter_trace_actors(
    actors: list[dict[str, Any]],
    actor_id: str | None = None,
    actor_kind: str | None = None,
) -> list[dict[str, Any]]:
    out = actors
    if actor_id:
        out = [a for a in out if a.get("actor_id") == actor_id]
    if actor_kind:
        out = [a for a in out if a.get("actor_kind") == actor_kind]
    return out


def universe_trace(args: argparse.Namespace, client: WorldForkClient) -> None:
    response = _fetch_universe_trace(
        client, args.universe_id, args.tick, args.include_raw
    )
    if not isinstance(response, dict):
        emit(args, response)
        return

    actors = response.get("actors", []) or []
    actors = _filter_trace_actors(actors, args.actor_id, args.actor_kind)

    actor_fields = parse_fields(args.fields)
    actor_keys = resolve_verbosity_keys("universe_trace_actor", args.verbosity, actor_fields)
    projected_actors = project_list(actors, actor_keys)

    # Build envelope. In summary mode we replace the actors array with a count.
    envelope_keys = resolve_verbosity_keys("universe_trace_envelope", args.verbosity, None)
    envelope = dict(response)
    envelope["actors"] = projected_actors
    if args.verbosity == "summary":
        envelope["actor_count"] = len(projected_actors)
    if args.verbosity == "normal" and isinstance(envelope.get("god_decision"), str):
        envelope["god_decision"] = truncate(envelope["god_decision"], 200)

    emit(args, project(envelope, envelope_keys))


def universe_actors(args: argparse.Namespace, client: WorldForkClient) -> None:
    """Discovery: list every actor in a universe at a given tick.

    Implementation: fetch the tick trace, project each actor to a small
    identifier-only shape. Fully client-side; no dedicated server endpoint.
    """
    response = _fetch_universe_trace(
        client, args.universe_id, args.tick, include_raw=False
    )
    if not isinstance(response, dict):
        emit(args, response)
        return

    actors = response.get("actors", []) or []
    rows = [
        {
            "actor_id": str(a.get("actor_id", "")),
            "actor_kind": str(a.get("actor_kind", "")),
            "job_type": str(a.get("job_type", "")),
        }
        for a in actors
    ]
    if args.json:
        emit(args, rows)
        return
    if not rows:
        print(f"No actors found in {args.universe_id} at tick {args.tick}.")
        return
    print(f"Actors in {args.universe_id} at tick {args.tick}: {len(rows)}")
    print_table(rows, ["actor_id", "actor_kind", "job_type"])


def cohort_transcript(args: argparse.Namespace, client: WorldForkClient) -> None:
    """Walk one cohort's row across a tick range, applying verbosity/fields.

    No server endpoint exposes "give me one cohort across N ticks" — we
    iterate ``universe trace`` calls and stitch the matching actor row from
    each. For long ranges this is N HTTP calls. Use ``--from-tick``/``--to-tick``
    to bound it.
    """
    if args.from_tick > args.to_tick:
        raise RuntimeError(
            f"--from-tick ({args.from_tick}) must be <= --to-tick ({args.to_tick})"
        )

    field_override = parse_fields(args.fields)
    keys = resolve_verbosity_keys("cohort_transcript_row", args.verbosity, field_override)

    rows: list[dict[str, Any]] = []
    for tick in range(args.from_tick, args.to_tick + 1):
        trace = _fetch_universe_trace(
            client, args.universe_id, tick, args.include_raw
        )
        if not isinstance(trace, dict):
            continue
        match = next(
            (
                a
                for a in trace.get("actors", []) or []
                if a.get("actor_id") == args.cohort_id
            ),
            None,
        )
        if match is None:
            rows.append({"tick": tick, "missing": True})
            continue
        # Always include tick; project the rest per verbosity/fields.
        projected = project(match, keys) if keys is not None else dict(match)
        projected = {"tick": tick, **projected}
        rows.append(projected)

    if args.json:
        emit(args, rows)
        return

    if not rows:
        print("No ticks in range.")
        return

    # Pick stable display columns from the first non-missing row.
    sample = next((r for r in rows if "missing" not in r), rows[0])
    columns = [k for k in sample.keys() if k != "missing"]
    if "tick" not in columns:
        columns.insert(0, "tick")
    # Stringify nested fields so they render in the table.
    flat_rows: list[dict[str, Any]] = []
    for r in rows:
        if r.get("missing"):
            flat_rows.append({"tick": r["tick"], **{c: "(missing)" for c in columns if c != "tick"}})
            continue
        flat = {}
        for c in columns:
            v = r.get(c, "")
            flat[c] = v if isinstance(v, (str, int, float)) else safe_json_dump(v).replace("\n", " ")
        flat_rows.append(flat)
    print(
        f"Cohort {args.cohort_id} transcript in {args.universe_id} "
        f"(ticks {args.from_tick}–{args.to_tick}, verbosity={args.verbosity})"
    )
    print_table(flat_rows, columns)


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------

def logs_list(args: argparse.Namespace, client: WorldForkClient, scope: str) -> None:
    params: dict[str, Any] = {"limit": args.limit, "offset": args.offset}
    for key in ("run_id", "universe_id", "provider", "status"):
        value = getattr(args, key, None)
        if value:
            params[key] = value

    response = client.request("GET", f"/logs/{scope}", params=params)

    # Project rows per verbosity / --fields. Skipped entirely if response
    # isn't a list (e.g. server returned an envelope shape we don't recognize).
    if isinstance(response, list):
        field_override = parse_fields(getattr(args, "fields", None))
        keys = resolve_verbosity_keys(f"logs_{scope}_row", args.verbosity, field_override)
        if args.verbosity == "summary" and scope == "errors":
            response = [
                {**row, "error": truncate(row.get("error", ""), 120)}
                if isinstance(row, dict)
                else row
                for row in response
            ]
        response = project_list(
            [r if isinstance(r, dict) else {"value": r} for r in response],
            keys,
        )

    if args.json:
        emit(args, response)
        return

    if scope == "errors":
        if not response:
            print("No error logs.")
            return
        for item in response:
            if not isinstance(item, dict):
                print(item)
                continue
            print(
                f"[{item.get('source', 'error')}] "
                f"{item.get('status')} {item.get('error')}"
            )
            extras = []
            if item.get("id"):
                extras.append(f"id: {item['id']}")
            if item.get("run_id"):
                extras.append(f"run: {short_id(item['run_id'])}")
            if extras:
                print("  " + " | ".join(extras))
            print()
        return

    emit(args, response)
