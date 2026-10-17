"""Privacy-report oracle: sanitize fixtures, stable fingerprint, markdown."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.privacy_report import (
    build_report_markdown,
    fingerprint_crash,
    sanitize_report_text,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2] / "schemas" / "golden-path" / "sanitize-fixtures.json"
)


def test_sanitize_treats_none_as_empty() -> None:
    assert sanitize_report_text(None) == ""


def test_sanitize_redacts_fixture_secrets() -> None:
    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    out = sanitize_report_text(fixture["stack"], stack=True)
    for leak in fixture["must_not_contain"]:
        assert leak not in out
    for keep in fixture["must_contain"]:
        assert keep in out


def test_fingerprint_stable_when_only_username_changes() -> None:
    a = fingerprint_crash("Error\n    at C:\\Users\\Ada\\app\\main.py:1")
    b = fingerprint_crash("Error\n    at C:\\Users\\Bob\\app\\main.py:1")
    assert a == b
    assert len(a) == 12


def test_markdown_strips_tokens_from_description() -> None:
    md = build_report_markdown(
        kind="crash",
        description="user ghp_abcdefghijklmnopqrstuvwxyz012345 leaked",
    )
    assert "ghp_" not in md
    assert "crash" in md
