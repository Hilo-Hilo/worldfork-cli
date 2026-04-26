"""Argument parser and entry point for the ``worldfork`` CLI."""

from __future__ import annotations

import argparse
import sys

from worldfork import __version__, commands
from worldfork.client import (
    DEFAULT_API_PREFIX,
    DEFAULT_BASE_URL,
    DEFAULT_ENV_FILE,
    DEFAULT_TIMEOUT,
    WorldForkClient,
)
from worldfork.output import DEFAULT_VERBOSITY, VERBOSITY_TIERS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="worldfork",
        description="Text-first CLI for a WorldFork backend.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=(
            "Base URL for the backend "
            "(default: $WORLD_FORK_API_BASE / $BACKEND_API_BASE / http://127.0.0.1:8003)"
        ),
    )
    parser.add_argument(
        "--api-prefix",
        default=DEFAULT_API_PREFIX,
        help="API prefix (default: /api)",
    )
    parser.add_argument(
        "--timeout",
        default=DEFAULT_TIMEOUT,
        type=float,
        help="HTTP timeout seconds (default: none — wait indefinitely; pass a number to cap)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw JSON for machine consumption",
    )
    parser.add_argument(
        "--env-file",
        default=DEFAULT_ENV_FILE,
        help="Env file path used by `set-key` (default: ./.env)",
    )
    parser.add_argument(
        "--verbosity",
        choices=list(VERBOSITY_TIERS),
        default=DEFAULT_VERBOSITY,
        help=(
            "How much detail to keep per record. 'summary' keeps just identifiers, "
            "'normal' keeps key business fields, 'full' keeps the raw API response. "
            f"Default: {DEFAULT_VERBOSITY}. Use 'summary' first when exploring."
        ),
    )

    sub = parser.add_subparsers(dest="command", required=True)

    _add_status(sub)
    _add_set_key(sub)
    _add_query(sub)
    _add_search(sub)
    _add_troubleshoot(sub)
    _add_bigbang(sub)
    _add_runs(sub)
    _add_multiverse(sub)
    _add_universe(sub)
    _add_cohort(sub)
    _add_model(sub)
    _add_jobs(sub)
    _add_logs(sub)

    return parser


def _add_status(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("status", help="Show backend health and current Big Bang count")
    p.set_defaults(func=lambda a, c: commands.status(a, c))


def _add_set_key(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("set-key", help="Write a KEY=VALUE pair into the local env file")
    p.add_argument("key")
    p.add_argument("value")
    p.set_defaults(func=lambda a, c: commands.set_key(a))


def _add_query(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("query", help="Run an arbitrary backend API request")
    p.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    p.add_argument("path", help="API path, e.g. /big-bangs")
    p.add_argument("--data", help="JSON string payload")
    p.add_argument("--payload-file", help="Path to a JSON payload file")
    p.set_defaults(func=commands.query)


def _add_search(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("search", help="DuckDuckGo web search (no backend involvement)")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=6)
    p.set_defaults(func=lambda a, c: commands.search(a))


def _add_troubleshoot(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("troubleshoot", help="Health + recent error log summary")
    p.add_argument("--run-id", dest="run_id")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--include-jobs", action="store_true")
    p.set_defaults(func=commands.troubleshoot)


def _add_bigbang(sub: argparse._SubParsersAction) -> None:
    bb = sub.add_parser("bigbang", help="Manage Big Bang runs")
    s = bb.add_subparsers(dest="bigbang_command", required=True)

    p = s.add_parser("list", help="List Big Bangs")
    p.set_defaults(func=commands.bigbang_list)

    p = s.add_parser("create", help="Create a Big Bang")
    p.add_argument("name")
    p.add_argument("--description")
    p.add_argument("--scenario-text", help="Scenario text inline (or piped via stdin)")
    p.add_argument("--payload", help="Path to JSON object payload")
    p.set_defaults(func=commands.bigbang_create)

    for action in ("start", "pause", "resume"):
        p = s.add_parser(action, help=f"{action.capitalize()} a Big Bang")
        p.add_argument("big_bang_id")
        p.set_defaults(func=lambda a, c, _a=action: commands.bigbang_action(a, c, _a))

    p = s.add_parser(
        "run-until-complete",
        help="Run a Big Bang to completion (default: enqueue async; --sync to block)",
    )
    p.add_argument("big_bang_id")
    p.add_argument("--max-ticks", type=int, default=24)
    p.add_argument(
        "--sync",
        action="store_true",
        help="Block the CLI on the API call until the simulation finishes (slow).",
    )
    p.set_defaults(func=commands.bigbang_run_until_complete)

    p = s.add_parser("reports", help="List reports for a Big Bang")
    p.add_argument("big_bang_id")
    p.set_defaults(func=commands.bigbang_reports)

    p = s.add_parser("final-report", help="Generate the final report")
    p.add_argument("big_bang_id")
    p.add_argument("--title")
    p.add_argument("--summary")
    p.set_defaults(func=commands.bigbang_final_report)


def _add_runs(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("runs", help="List run metadata")
    p.add_argument("--status")
    p.add_argument("--q")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=commands.run_list)


def _add_multiverse(sub: argparse._SubParsersAction) -> None:
    mv = sub.add_parser("multiverse", help="Dependency graph and tick controls")
    s = mv.add_subparsers(dest="multiverse_command", required=True)

    p = s.add_parser("tree", help="Get run dependency snapshot")
    p.add_argument("big_bang_id")
    p.set_defaults(func=commands.multiverse_tree)

    p = s.add_parser("dag", help="Render multiverse dependency DAG")
    p.add_argument("big_bang_id")
    p.set_defaults(func=commands.multiverse_dag)

    p = s.add_parser("metrics", help="Aggregate metrics for a multiverse")
    p.add_argument("big_bang_id")
    p.set_defaults(func=commands.multiverse_metrics)

    p = s.add_parser("step", help="Queue one tick across active universes")
    p.add_argument("big_bang_id")
    p.set_defaults(func=commands.multiverse_step)


def _add_universe(sub: argparse._SubParsersAction) -> None:
    uni = sub.add_parser("universe", help="Universe-level interventions")
    s = uni.add_subparsers(dest="universe_command", required=True)

    p = s.add_parser("step", help="Simulate a single universe tick")
    p.add_argument("universe_id")
    p.add_argument("--tick", type=int)
    p.set_defaults(func=commands.universe_step)

    p = s.add_parser("force-deviation", help="Force manual intervention at a tick")
    p.add_argument("universe_id")
    p.add_argument("tick", type=int)
    p.add_argument(
        "--mode",
        choices=["god_prompt", "structured_delta"],
        default="god_prompt",
    )
    p.add_argument("--reason", default="")
    p.add_argument("--prompt")
    p.add_argument("--prompt-file")
    p.add_argument("--delta", help="Structured delta JSON string")
    p.add_argument("--delta-file", help="Structured delta JSON file")
    p.add_argument("--no-auto-start", dest="auto_start", action="store_false")
    p.set_defaults(func=commands.universe_force_deviation)

    p = s.add_parser("actors", help="List actors (cohorts/gods/heroes) in a universe")
    p.add_argument("universe_id")
    p.add_argument(
        "--tick",
        type=int,
        default=1,
        help="Tick to inspect actors at (default: 1; cohorts persist across ticks).",
    )
    p.set_defaults(func=commands.universe_actors)

    p = s.add_parser(
        "trace",
        help="Pull trace for a universe tick (filterable by actor; verbosity-aware)",
    )
    p.add_argument("universe_id")
    p.add_argument("tick", type=int)
    p.add_argument("--include-raw", action="store_true", help="Pass include_raw=true to the API.")
    p.add_argument(
        "--actor-id",
        dest="actor_id",
        help="Keep only the actor with this id (e.g. coh_…, hero_…, god_…).",
    )
    p.add_argument(
        "--actor-kind",
        dest="actor_kind",
        choices=["cohort", "god", "hero"],
        help="Keep only actors of this kind.",
    )
    p.add_argument(
        "--fields",
        help=(
            "Comma-separated top-level keys to keep on each actor "
            "(overrides --verbosity; e.g. --fields actor_id,rationale,state_delta)."
        ),
    )
    p.set_defaults(func=commands.universe_trace)


def _add_cohort(sub: argparse._SubParsersAction) -> None:
    co = sub.add_parser(
        "cohort",
        help="Cohort-level views (transcript walks across ticks)",
    )
    s = co.add_subparsers(dest="cohort_command", required=True)

    p = s.add_parser(
        "transcript",
        help="Walk one cohort's row across a tick range, applying --verbosity/--fields.",
    )
    p.add_argument("universe_id")
    p.add_argument("cohort_id", help="Actor id of the cohort (e.g. coh_…).")
    p.add_argument("--from-tick", dest="from_tick", type=int, required=True)
    p.add_argument("--to-tick", dest="to_tick", type=int, required=True)
    p.add_argument("--include-raw", action="store_true")
    p.add_argument(
        "--fields",
        help="Comma-separated keys to keep per tick (overrides --verbosity).",
    )
    p.set_defaults(func=commands.cohort_transcript)


def _add_model(sub: argparse._SubParsersAction) -> None:
    """Live, hot model swap. Wraps PATCH /api/settings/model-routing.

    The backend keeps a per-job-type routing table in the DB. Mutating it
    takes effect on the next worker call — no container restart, no env edit.
    """
    mo = sub.add_parser(
        "model",
        help="Live model routing (per-job-type preferred + fallback). Hot-swap; no restart.",
    )
    s = mo.add_subparsers(dest="model_command", required=True)

    p = s.add_parser("list", help="Show the current routing table for every job_type.")
    p.set_defaults(func=commands.model_list)

    p = s.add_parser("get", help="Show the routing entry for one job_type.")
    p.add_argument("job_type")
    p.set_defaults(func=commands.model_get)

    p = s.add_parser(
        "set",
        help=(
            "Swap the preferred (and optionally fallback) model. "
            "Default scope: every job_type (--all). Use --job-type to scope to one."
        ),
    )
    p.add_argument("model", help="OpenRouter slug, e.g. google/gemini-3.1-flash-lite-preview")
    p.add_argument(
        "--job-type",
        dest="job_type",
        help="Scope to one job_type (e.g. simulate_universe_tick). Omit to apply to all.",
    )
    p.add_argument("--all", action="store_true", help="Apply to every job_type (default).")
    p.add_argument(
        "--fallback",
        default="deepseek/deepseek-v4-pro",
        help=(
            "Fallback model on the same scope "
            "(default: deepseek/deepseek-v4-pro). "
            "Pass an empty string to leave the existing fallback untouched."
        ),
    )
    p.add_argument(
        "--provider",
        default="openrouter",
        help="Preferred provider (default: openrouter).",
    )
    p.add_argument(
        "--fallback-provider",
        dest="fallback_provider",
        default="openrouter",
        help="Fallback provider (default: openrouter).",
    )
    p.set_defaults(func=commands.model_set)


def _add_jobs(sub: argparse._SubParsersAction) -> None:
    j = sub.add_parser("jobs", help="Inspect and trigger background jobs")
    s = j.add_subparsers(dest="jobs_command", required=True)

    p = s.add_parser("types", help="List registered job types")
    p.set_defaults(func=commands.jobs_types)

    p = s.add_parser("list", help="List recent jobs")
    p.add_argument("--big-bang-id")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=commands.jobs_list)

    p = s.add_parser("create", help="Enqueue a job")
    p.add_argument("job_type")
    p.add_argument("--big-bang-id")
    p.add_argument("--payload", required=True, help="JSON payload string")
    p.add_argument("--idempotency-key")
    p.set_defaults(func=commands.jobs_create)

    p = s.add_parser("run", help="Run a queued job inline (server-side)")
    p.add_argument("job_id")
    p.set_defaults(func=commands.jobs_run)


def _add_logs(sub: argparse._SubParsersAction) -> None:
    lg = sub.add_parser("logs", help="Inspect API and job logs")
    s = lg.add_subparsers(dest="logs_command", required=True)

    common_filters = ("run_id", "universe_id", "provider", "status")
    # Every scope reuses the same handler; flags it doesn't declare are read
    # via getattr() in commands.logs_list, so missing flags are not errors.

    p = s.add_parser("requests", help="LLM/provider request logs")
    p.add_argument("--run-id")
    p.add_argument("--universe-id")
    p.add_argument("--provider")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--fields", help="Comma-separated keys to keep per row (overrides --verbosity).")
    p.set_defaults(func=lambda a, c: commands.logs_list(a, c, "requests"))

    p = s.add_parser("errors", help="Error logs")
    p.add_argument("--run-id")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--fields", help="Comma-separated keys to keep per row (overrides --verbosity).")
    p.set_defaults(func=lambda a, c: commands.logs_list(a, c, "errors"))

    p = s.add_parser("webhooks", help="Webhook delivery logs")
    p.add_argument("--run-id")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--fields", help="Comma-separated keys to keep per row (overrides --verbosity).")
    p.set_defaults(func=lambda a, c: commands.logs_list(a, c, "webhooks"))

    p = s.add_parser("audit", help="Audit logs")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--fields", help="Comma-separated keys to keep per row (overrides --verbosity).")
    p.set_defaults(func=lambda a, c: commands.logs_list(a, c, "audit"))

    _ = common_filters  # reserved for future shared-arg refactor


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = WorldForkClient(args.base_url, api_prefix=args.api_prefix, timeout=args.timeout)
    try:
        args.func(args, client)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
