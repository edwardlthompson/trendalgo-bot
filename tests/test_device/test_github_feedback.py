"""GitHub issue-form URL composer and fail-soft duplicate search."""

from __future__ import annotations

from trendalgo.device.github_feedback.cooldown import Cooldown
from trendalgo.device.github_feedback.duplicate_search import (
    parse_search_items,
    search_duplicate_issues,
)
from trendalgo.device.github_feedback.issue_form_url import (
    MAX_QUERY_CHARS,
    build_issue_form_url,
    crash_title,
    is_placeholder_repo,
)


def test_crash_title_formats_fingerprint_and_type() -> None:
    assert crash_title("A1B2C3D4E5F6ffff", "TypeError: x") == "[crash] a1b2c3d4e5f6 TypeError"


def test_is_placeholder_repo() -> None:
    assert is_placeholder_repo("") is True
    assert is_placeholder_repo("OWNER/REPO") is True
    assert is_placeholder_repo("acme/app") is False


def test_build_issue_form_url_empty_for_placeholder() -> None:
    assert build_issue_form_url("OWNER/REPO", "crash_report.yml", {"description": "x"})["url"] == ""


def test_build_issue_form_url_prefills_small_fields() -> None:
    built = build_issue_form_url(
        "acme/app",
        "crash_report.yml",
        {"title": "[crash] abc TypeError", "description": "boom"},
    )
    assert built["body_too_large"] is False
    assert "github.com/acme/app/issues/new" in str(built["url"])
    assert "template=crash_report.yml" in str(built["url"])


def test_build_issue_form_url_drops_large_stack() -> None:
    stack = "x" * (MAX_QUERY_CHARS + 500)
    built = build_issue_form_url(
        "acme/app", "crash_report.yml", {"stack": stack, "title": "[crash] ab"}
    )
    assert built["body_too_large"] is True
    assert len(str(built["url"])) < MAX_QUERY_CHARS
    assert stack[:40] not in str(built["url"])
    assert built["clipboard_markdown"] == stack


def test_search_does_not_fetch_placeholder() -> None:
    calls: list[str] = []

    def fetch(url: str, _headers: dict[str, str]) -> dict[str, object]:
        calls.append(url)
        return {"items": []}

    assert search_duplicate_issues("OWNER/REPO", "abc", fetch_impl=fetch) == []
    assert calls == []


def test_search_reuses_cache_inside_60s() -> None:
    now = {"t": 1000.0}
    cd: Cooldown[list[object]] = Cooldown(lambda: now["t"])
    calls = {"n": 0}

    def fetch(_url: str, _headers: dict[str, str]) -> dict[str, object]:
        calls["n"] += 1
        return {"items": [{"title": "t", "html_url": "https://x", "number": 1}]}

    first = search_duplicate_issues("acme/app", "abc", fetch_impl=fetch, cooldown=cd)  # type: ignore[arg-type]
    now["t"] += 1000.0
    second = search_duplicate_issues("acme/app", "abc", fetch_impl=fetch, cooldown=cd)  # type: ignore[arg-type]
    assert first == second
    assert calls["n"] == 1


def test_parse_search_items() -> None:
    assert parse_search_items([{"title": "t", "html_url": "https://x", "number": 2}])[0].number == 2
    assert parse_search_items(None) == []
