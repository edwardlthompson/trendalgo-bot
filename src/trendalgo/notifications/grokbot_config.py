"""Grok Bot webhook env (opt-in, off by default)."""

from __future__ import annotations

import os
from typing import Any

URL_ENV = "GROKBOT_WEBHOOK_URL"
KEY_ENV = "GROKBOT_WEBHOOK_KEY"
HEADER_ENV = "GROKBOT_WEBHOOK_HEADER"
SCHEME_ENV = "GROKBOT_WEBHOOK_SCHEME"
DEFAULT_HEADER = "Authorization"
DEFAULT_SCHEME = "Bearer"
TIMEOUT_SEC = 5.0
SPARKLINE_MAX = 48


def webhook_url() -> str:
    return os.environ.get(URL_ENV, "").strip()


def grokbot_enabled() -> bool:
    """On only when an HTTPS URL is set. HTTP is refused (send-only channel)."""
    return webhook_url().lower().startswith("https://")


def sender_key() -> str:
    return os.environ.get(KEY_ENV, "").strip()


def header_name() -> str:
    return os.environ.get(HEADER_ENV, "").strip() or DEFAULT_HEADER


def header_scheme() -> str:
    raw = os.environ.get(SCHEME_ENV)
    if raw is None:
        return DEFAULT_SCHEME if header_name().lower() == "authorization" else ""
    return raw.strip()


def auth_headers() -> dict[str, str]:
    key = sender_key()
    if not key:
        return {}
    scheme = header_scheme()
    value = f"{scheme} {key}".strip() if scheme else key
    return {header_name(): value}


def bot_mode() -> str:
    raw = os.environ.get("TRENDALGO_MODE", "dry-run").strip().lower()
    if raw in {"live", "production"}:
        return "live"
    return "dry-run"


def public_status() -> dict[str, Any]:
    """Status for UI/API — never includes the URL or key."""
    return {
        "enabled": grokbot_enabled(),
        "header": header_name(),
        "scheme": header_scheme() or None,
        "key_configured": bool(sender_key()),
    }
