"""Grok Bot HTTPS webhook sink — fire-and-forget, never blocks Telegram or trading."""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from trendalgo.notifications.grokbot_config import (
    TIMEOUT_SEC,
    auth_headers,
    grokbot_enabled,
    webhook_url,
)
from trendalgo.notifications.grokbot_config import (
    public_status as config_status,
)
from trendalgo.notifications.grokbot_cooldown import (
    is_unavailable,
    mark_unavailable,
    remaining_seconds,
)
from trendalgo.notifications.grokbot_cooldown import (
    reset as reset_cooldown,
)
from trendalgo.notifications.grokbot_filter import event_allowed, event_tokens
from trendalgo.notifications.grokbot_http import urlopen as _urlopen
from trendalgo.notifications.grokbot_payload import envelope, test_payload

AI_BRIEF_NOTE = "AI brief unavailable"
_LOG = logging.getLogger("trendalgo.notifications.grokbot")
_on_log: Callable[[str], None] | None = None


def configure(*, on_log: Callable[[str], None] | None) -> None:
    global _on_log
    _on_log = on_log


def grok_unavailable() -> bool:
    return grokbot_enabled() and is_unavailable()


def telegram_ai_note(text: str) -> str:
    """Append a short note when Grok is already on cooldown. Never waits on HTTP."""
    if not grok_unavailable():
        return text
    if AI_BRIEF_NOTE in text:
        return text
    return f"{text}\n{AI_BRIEF_NOTE}"


def public_status() -> dict[str, Any]:
    status = config_status()
    status["events"] = sorted(event_tokens())
    status["unavailable"] = is_unavailable()
    status["cooldown_remaining_sec"] = round(remaining_seconds(), 1)
    return status


def emit(payload: dict[str, Any], *, wait: bool = False) -> dict[str, Any]:
    """POST one event after Telegram. Default is non-blocking; failures never raise."""
    if not grokbot_enabled():
        return {"sent": False, "reason": "disabled"}
    kind = str(payload.get("event_type") or "")
    tier = payload.get("tier")
    if not event_allowed(kind, tier=str(tier) if tier is not None else None):
        return {"sent": False, "reason": "filtered"}
    if is_unavailable():
        return {"sent": False, "reason": "grok unavailable"}
    if wait:
        return _post_safe(payload)
    try:
        threading.Thread(
            target=_post_safe, args=(payload,), daemon=True, name="grokbot-webhook"
        ).start()
    except Exception as exc:  # noqa: BLE001 — never break the caller
        _fail(f"grokbot: could not queue webhook ({exc})")
        return {"sent": False, "reason": str(exc)}
    return {"sent": True, "queued": True}


def emit_event(event_type: str, **fields: Any) -> dict[str, Any]:
    return emit(envelope(event_type=event_type, **fields))


def send_test(*, wait: bool = True) -> dict[str, Any]:
    if not grokbot_enabled():
        return {"sent": False, "reason": "GROKBOT_WEBHOOK_URL not set (https required)"}
    reset_cooldown()
    return emit(test_payload(), wait=wait)


def _post_safe(payload: dict[str, Any]) -> dict[str, Any]:
    result = _post_once(payload)
    if result.get("sent"):
        return result
    mark_unavailable()
    reason = str(result.get("reason") or "failed")
    _fail(f"grokbot: Grok unavailable ({reason})")
    return {"sent": False, "reason": reason, "unavailable": True}


def _post_once(payload: dict[str, Any]) -> dict[str, Any]:
    url = webhook_url()
    if not url.lower().startswith("https://"):
        return {"sent": False, "reason": "https required"}
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8", **auth_headers()}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _urlopen(req, timeout=TIMEOUT_SEC) as resp:
            code = int(resp.status)
            if 200 <= code < 300:
                return {"sent": True, "status": code}
            return {"sent": False, "reason": f"http {code}"}
    except urllib.error.HTTPError as exc:
        return {"sent": False, "reason": f"http {int(exc.code)}"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"sent": False, "reason": str(exc)}


def _fail(message: str) -> None:
    _LOG.warning(message)
    if _on_log is not None:
        try:
            _on_log(message)
        except Exception:  # noqa: BLE001
            return


__all__ = [
    "configure",
    "emit",
    "emit_event",
    "grok_unavailable",
    "grokbot_enabled",
    "public_status",
    "send_test",
    "telegram_ai_note",
]
