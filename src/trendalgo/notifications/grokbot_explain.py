"""Telegram Why? callback → Grok Bot explain_request (quota on demand)."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from trendalgo.notifications.grokbot_payload import envelope

PREFIX = "why:"
_DIRNAME = "grokbot-why"


def data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve() / _DIRNAME


def stash(payload: dict[str, Any]) -> str:
    token = uuid.uuid4().hex[:12]
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{token}.json").write_text(json.dumps(payload, default=str), encoding="utf-8")
    return token


def load(token: str) -> dict[str, Any] | None:
    path = data_dir() / f"{token}.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        path.unlink()
    except OSError:
        pass
    return raw if isinstance(raw, dict) else None


def why_markup(payload: dict[str, Any], existing: dict[str, Any] | str | None = None) -> str:
    rows: list[list[dict[str, str]]] = []
    if isinstance(existing, str) and existing.strip():
        parsed = json.loads(existing)
        existing = parsed if isinstance(parsed, dict) else None
    if isinstance(existing, dict):
        for row in existing.get("inline_keyboard") or []:
            if isinstance(row, list):
                rows.append(row)
    rows.append([{"text": "Why?", "callback_data": f"{PREFIX}{stash(payload)}"}])
    return json.dumps({"inline_keyboard": rows}, separators=(",", ":"))


def handle_why(callback_data: str) -> dict[str, Any]:
    """POST explain_request even when GROKBOT_WEBHOOK_EVENTS would filter the original."""
    from trendalgo.notifications.grokbot import emit

    raw = str(callback_data or "")
    if not raw.startswith(PREFIX):
        return {"sent": False, "reason": "ignored"}
    payload = load(raw[len(PREFIX) :])
    if not payload:
        return {"sent": False, "reason": "expired"}
    return emit(_explain_payload(payload), wait=True)


def _explain_payload(source: dict[str, Any]) -> dict[str, Any]:
    skip = {"event_type", "schema_version", "timestamp_utc"}
    fields = {key: value for key, value in source.items() if key not in skip}
    original = str(source.get("event_type") or "event")
    extra = str(source.get("reason") or source.get("rationale") or "").strip()
    fields["reason"] = f"explain {original}" + (f": {extra}" if extra else "")
    return envelope(event_type="explain_request", **fields)


def answer_callback(token: str | None, callback_id: str, text: str) -> bool:
    if not token or not callback_id:
        return False
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    body = parse.urlencode({"callback_query_id": callback_id, "text": text[:200]}).encode()
    try:
        req = request.Request(url, data=body, method="POST")
        with request.urlopen(req, timeout=10) as resp:
            return int(resp.status) == 200
    except (error.URLError, TimeoutError, OSError):
        return False
