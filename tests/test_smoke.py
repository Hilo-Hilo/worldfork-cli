"""Smoke tests that don't require a running backend."""

from __future__ import annotations

import pytest

from worldfork import __version__
from worldfork.cli import build_parser
from worldfork.output import (
    DEFAULT_VERBOSITY,
    VERBOSITY_TIERS,
    parse_fields,
    project,
    project_list,
    resolve_verbosity_keys,
    truncate,
)


def test_version_string_is_set() -> None:
    assert __version__


def test_parser_builds_and_lists_top_level_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    expected = [
        "status",
        "set-key",
        "query",
        "search",
        "troubleshoot",
        "bigbang",
        "runs",
        "multiverse",
        "universe",
        "cohort",
        "jobs",
        "logs",
    ]
    for cmd in expected:
        assert cmd in help_text, f"missing {cmd!r} in --help"


@pytest.mark.parametrize(
    "argv",
    [
        ["status"],
        ["bigbang", "list"],
        ["bigbang", "run-until-complete", "RUNID"],
        ["multiverse", "dag", "RUNID"],
        ["jobs", "list"],
        ["logs", "errors"],
        ["logs", "audit"],
        ["query", "GET", "/big-bangs"],
        ["universe", "actors", "UNIID"],
        ["universe", "trace", "UNIID", "1"],
        ["universe", "trace", "UNIID", "1", "--actor-kind", "cohort"],
        ["universe", "trace", "UNIID", "1", "--actor-id", "coh_X"],
        ["universe", "trace", "UNIID", "1", "--fields", "actor_id,rationale"],
        ["cohort", "transcript", "UNIID", "COHID", "--from-tick", "1", "--to-tick", "3"],
        ["logs", "requests", "--fields", "call_id,latency_ms"],
    ],
)
def test_subcommands_parse(argv: list[str]) -> None:
    parser = build_parser()
    parsed = parser.parse_args(argv)
    assert hasattr(parsed, "func")
    # Top-level --verbosity should always be readable, defaulting to "normal".
    assert parsed.verbosity == DEFAULT_VERBOSITY


@pytest.mark.parametrize("tier", VERBOSITY_TIERS)
def test_verbosity_tier_accepted(tier: str) -> None:
    parser = build_parser()
    parsed = parser.parse_args(["--verbosity", tier, "status"])
    assert parsed.verbosity == tier


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------

def test_project_keeps_only_requested_keys() -> None:
    obj = {"a": 1, "b": 2, "c": 3}
    assert project(obj, ["a", "c"]) == {"a": 1, "c": 3}


def test_project_skips_missing_keys_silently() -> None:
    obj = {"a": 1}
    assert project(obj, ["a", "missing"]) == {"a": 1}


def test_project_none_keys_returns_obj_unchanged() -> None:
    obj = {"a": 1, "b": 2}
    assert project(obj, None) is obj


def test_project_list_applies_to_each_item() -> None:
    items = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert project_list(items, ["a"]) == [{"a": 1}, {"a": 3}]


def test_parse_fields_handles_whitespace_and_empties() -> None:
    assert parse_fields("a, b ,c") == ["a", "b", "c"]
    assert parse_fields("") is None
    assert parse_fields(None) is None


def test_resolve_verbosity_keys_field_override_wins() -> None:
    assert resolve_verbosity_keys("universe_trace_actor", "summary", ["x"]) == ["x"]


def test_resolve_verbosity_keys_unknown_surface_means_no_projection() -> None:
    assert resolve_verbosity_keys("not_a_surface", "summary", None) is None


def test_resolve_verbosity_full_returns_none() -> None:
    assert resolve_verbosity_keys("universe_trace_actor", "full", None) is None


def test_truncate_only_strings() -> None:
    assert truncate("hello world", 5) == "hell…"
    assert truncate("short", 100) == "short"
    assert truncate(123, 2) == 123  # non-string passes through
