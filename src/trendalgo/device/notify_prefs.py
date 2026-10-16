"""Device notification channel preferences (profile JSON, not host portfolio prefs)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "notify_prefs.json"


@dataclass
class NotifyPrefs:
    watchlist_alerts: bool = True
    qualified_alerts: bool = True
    trade_alerts: bool = True
    telegram_enabled: bool = False
    telegram_watchlist: bool = True
    telegram_qualified: bool = True
    telegram_trades: bool = True
    start_with_windows: bool = True


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def load_prefs(root: Path) -> NotifyPrefs:
    raw = read_json(prefs_path(root))
    if not isinstance(raw, dict):
        return NotifyPrefs()
    return NotifyPrefs(
        watchlist_alerts=_bool(raw.get("watchlist_alerts"), True),
        qualified_alerts=_bool(raw.get("qualified_alerts"), True),
        trade_alerts=_bool(raw.get("trade_alerts"), True),
        telegram_enabled=_bool(raw.get("telegram_enabled"), False),
        telegram_watchlist=_bool(raw.get("telegram_watchlist"), True),
        telegram_qualified=_bool(raw.get("telegram_qualified"), True),
        telegram_trades=_bool(raw.get("telegram_trades"), True),
        start_with_windows=_bool(raw.get("start_with_windows"), True),
    )


def save_prefs(root: Path, prefs: NotifyPrefs) -> None:
    write_json(prefs_path(root), asdict(prefs))


def _bool(raw: Any, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    return default
