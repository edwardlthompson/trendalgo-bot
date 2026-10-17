"""Feedback markdown preview: sanitize tokens; require description or stack."""

from __future__ import annotations

from trendalgo.device.feedback.preview import can_submit_feedback, feedback_preview_text


def test_never_keeps_a_token_in_the_preview_string() -> None:
    text = feedback_preview_text(
        kind="bug",
        description="<img src=x onerror=alert(1)> ghp_abcdefghijklmnopqrstuvwxyz012345",
    )
    assert "ghp_" not in text
    assert "<redacted-secret>" in text


def test_requires_description_or_stack() -> None:
    assert can_submit_feedback("") is False
    assert can_submit_feedback("  ") is False
    assert can_submit_feedback("steps") is True
    assert can_submit_feedback("", "Traceback") is True
