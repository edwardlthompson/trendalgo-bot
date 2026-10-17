"""Shared sanitizer, fingerprint, and markdown builder. No UI and no network."""

from trendalgo.device.privacy_report.fingerprint import fingerprint_crash
from trendalgo.device.privacy_report.markdown import build_report_markdown
from trendalgo.device.privacy_report.sanitize import sanitize_report_text

__all__ = ["build_report_markdown", "fingerprint_crash", "sanitize_report_text"]
