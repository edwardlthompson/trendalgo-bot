"""Deep-link Feedback entry: sanitize subject; invalid payloads fall back safely."""

from __future__ import annotations

from trendalgo.device.deep_link import feedback_link_from_argv, parse_feedback_deep_link


def test_parses_feedback_link_with_sanitized_subject() -> None:
    link = parse_feedback_deep_link(
        "trendalgo://settings/about/feedback?subject=boom%20ghp_abcdefghijklmnopqrstuvwxyz012345"
    )
    assert link is not None
    assert link.kind == "bug"
    assert "ghp_" not in link.subject
    assert "<redacted-secret>" in link.subject


def test_invalid_payload_returns_none_or_empty_subject() -> None:
    assert parse_feedback_deep_link("trendalgo://other") is None
    bare = parse_feedback_deep_link("trendalgo://settings/about/feedback")
    assert bare is not None
    assert bare.subject == ""


def test_argv_helper() -> None:
    link = feedback_link_from_argv(
        ["trendalgo-device", "trendalgo://settings/about/feedback?kind=feature&text=idea"]
    )
    assert link is not None
    assert link.kind == "feature"
    assert "idea" in link.subject
