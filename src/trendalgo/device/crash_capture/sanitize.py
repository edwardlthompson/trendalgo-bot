"""Re-export: canonical sanitizer lives in privacy_report."""

from trendalgo.device.privacy_report.sanitize import (
    MAX_BODY_BYTES,
    MAX_STACK_LINES,
    sanitize_report_text,
)

__all__ = ["MAX_BODY_BYTES", "MAX_STACK_LINES", "sanitize_report_text"]
