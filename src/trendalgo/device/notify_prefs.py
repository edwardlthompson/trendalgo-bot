"""Device notification channel preferences (profile JSON, not host portfolio prefs)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "notify_prefs.json"


@dataclass
class NotifyPrefs:
    # Windows (OS toast) per kind
    windows_logs: bool = False
    windows_entered: bool = True
    windows_left: bool = True
    windows_trades: bool = True
    # Telegram master + per kind
    telegram_enabled: bool = False
    telegram_logs: bool = False
    telegram_entered: bool = True
    telegram_left: bool = True
    telegram_trades: bool = True
    start_with_windows: bool = True

    # Legacy aliases used by older tests / host sync
    @property
    def watchlist_alerts(self) -> bool:
        return self.windows_left

    @property
    def qualified_alerts(self) -> bool:
        return self.windows_entered

    @property
    def trade_alerts(self) -> bool:
        return self.windows_trades

    @property
    def telegram_watchlist(self) -> bool:
        return self.telegram_left

    @property
    def telegram_qualified(self) -> bool:
        return self.telegram_entered


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def load_prefs(root: Path) -> NotifyPrefs:
    raw = read_json(prefs_path(root))
    if not isinstance(raw, dict):
        return NotifyPrefs()
    # Prefer new keys; fall back to legacy event masters.
    return NotifyPrefs(
        windows_logs=_bool(raw.get("windows_logs"), False),
        windows_entered=_bool(raw.get("windows_entered"), _bool(raw.get("qualified_alerts"), True)),
        windows_left=_bool(raw.get("windows_left"), _bool(raw.get("watchlist_alerts"), True)),
        windows_trades=_bool(raw.get("windows_trades"), _bool(raw.get("trade_alerts"), True)),
        telegram_enabled=_bool(raw.get("telegram_enabled"), False),
        telegram_logs=_bool(raw.get("telegram_logs"), False),
        telegram_entered=_bool(
            raw.get("telegram_entered"), _bool(raw.get("telegram_qualified"), True)
        ),
        telegram_left=_bool(raw.get("telegram_left"), _bool(raw.get("telegram_watchlist"), True)),
        telegram_trades=_bool(raw.get("telegram_trades"), True),
        start_with_windows=_bool(raw.get("start_with_windows"), True),
    )


def save_prefs(root: Path, prefs: NotifyPrefs) -> None:
    payload = asdict(prefs)
    # Keep legacy keys so older readers stay coherent.
    payload["watchlist_alerts"] = prefs.windows_left
    payload["qualified_alerts"] = prefs.windows_entered
    payload["trade_alerts"] = prefs.windows_trades
    payload["telegram_watchlist"] = prefs.telegram_left
    payload["telegram_qualified"] = prefs.telegram_entered
    write_json(prefs_path(root), payload)


def _bool(raw: Any, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    return default
