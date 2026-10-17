"""Escaped feedback preview — callers must set plain text, never rich HTML."""

from __future__ import annotations

from trendalgo.device.privacy_report.markdown import build_report_markdown
from trendalgo.device.privacy_report.sanitize import sanitize_report_text


def feedback_preview_text(
    *,
    kind: str,
    description: str | None = None,
    stack: str | None = None,
    fingerprint: str | None = None,
    app_version: str | None = None,
    os_family: str | None = None,
) -> str:
    return build_report_markdown(
        kind=kind,
        description=sanitize_report_text(description),
        stack=stack,
        fingerprint=fingerprint,
        app_version=app_version,
        os_family=os_family,
    )


def can_submit_feedback(description: str, stack: str | None = None) -> bool:
    return bool(
        sanitize_report_text(description).strip() or sanitize_report_text(stack, stack=True).strip()
    )
