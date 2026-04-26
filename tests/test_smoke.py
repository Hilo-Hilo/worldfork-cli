"""Smoke tests that don't require a running backend."""

from __future__ import annotations

import pytest

from worldfork import __version__
from worldfork.cli import build_parser


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
    ],
)
def test_subcommands_parse(argv: list[str]) -> None:
    parser = build_parser()
    parsed = parser.parse_args(argv)
    assert hasattr(parsed, "func")
