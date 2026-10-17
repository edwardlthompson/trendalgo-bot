"""Compose GitHub issue-form URLs and fail-soft duplicate search."""

from trendalgo.device.github_feedback.issue_form_url import (
    build_issue_form_url,
    crash_title,
    is_placeholder_repo,
)

__all__ = ["build_issue_form_url", "crash_title", "is_placeholder_repo"]
