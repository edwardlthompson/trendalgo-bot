"""Host-side Telegram credentials (OS-permission file; Linux VPS has no CredMgr)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SECRETS_NAME = "telegram_secrets.json"
PREFS_NAME = "notify_prefs.json"


def secrets_path(root: Path) -> Path:
    return root / SECRETS_NAME


def prefs_path(root: Path) -> Path:
    return root / PREFS_NAME


def load_creds(root: Path) -> tuple[str | None, str | None]:
    raw = _read(secrets_path(root))
    if not isinstance(raw, dict):
        return None, None
    token = str(raw.get("bot_token") or "").strip() or None
    chat = str(raw.get("chat_id") or "").strip() or None
    return token, chat


def save_creds(root: Path, *, bot_token: str, chat_id: str) -> None:
    path = secrets_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"bot_token": bot_token.strip(), "chat_id": chat_id.strip()}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_trade_alerts(root: Path) -> bool:
    raw = _read(prefs_path(root))
    if not isinstance(raw, dict):
        return True
    value = raw.get("trade_alerts")
    return True if not isinstance(value, bool) else value


def save_notify_flags(
    root: Path,
    *,
    trade_alerts: bool = True,
    telegram_enabled: bool = True,
    telegram_trades: bool = True,
) -> None:
    path = prefs_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "trade_alerts": trade_alerts,
                "telegram_enabled": telegram_enabled,
                "telegram_trades": telegram_trades,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def trade_notify_allowed(root: Path) -> bool:
    raw = _read(prefs_path(root))
    if not isinstance(raw, dict):
        return True
    trade = raw.get("trade_alerts", True)
    enabled = raw.get("telegram_enabled", True)
    mirror = raw.get("telegram_trades", True)
    return bool(trade and enabled and mirror)


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
