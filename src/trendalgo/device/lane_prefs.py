"""Per-desk Auto-scan prefs (Crypto / TradFi / Forex)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

LaneId = Literal["crypto", "tradfi", "forex"]

_FILE = "lane_prefs.json"


@dataclass(frozen=True)
class LanePrefs:
    auto_scan_crypto: bool = True
    auto_scan_tradfi: bool = False
    auto_scan_forex: bool = False

    def auto_scan(self, lane: LaneId) -> bool:
        if lane == "crypto":
            return self.auto_scan_crypto
        if lane == "tradfi":
            return self.auto_scan_tradfi
        return self.auto_scan_forex

    def with_auto_scan(self, lane: LaneId, enabled: bool) -> LanePrefs:
        if lane == "crypto":
            return LanePrefs(enabled, self.auto_scan_tradfi, self.auto_scan_forex)
        if lane == "tradfi":
            return LanePrefs(self.auto_scan_crypto, enabled, self.auto_scan_forex)
        return LanePrefs(self.auto_scan_crypto, self.auto_scan_tradfi, enabled)


def default_lane_prefs() -> LanePrefs:
    return LanePrefs()


def _bool_from(raw: dict[str, Any], *keys: str, default: bool) -> bool:
    for key in keys:
        if key in raw:
            return bool(raw[key])
    return default


def load_lane_prefs(root: Path) -> LanePrefs:
    path = root / _FILE
    if not path.is_file():
        return default_lane_prefs()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_lane_prefs()
    if not isinstance(raw, dict):
        return default_lane_prefs()
    return LanePrefs(
        auto_scan_crypto=_bool_from(
            raw, "auto_scan_crypto", "hourly_crypto", "show_crypto", default=True
        ),
        auto_scan_tradfi=_bool_from(
            raw, "auto_scan_tradfi", "hourly_tradfi", "show_tradfi", default=False
        ),
        auto_scan_forex=_bool_from(
            raw, "auto_scan_forex", "hourly_forex", "show_forex", default=False
        ),
    )


def save_lane_prefs(root: Path, prefs: LanePrefs) -> None:
    path = root / _FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "auto_scan_crypto": prefs.auto_scan_crypto,
        "auto_scan_tradfi": prefs.auto_scan_tradfi,
        "auto_scan_forex": prefs.auto_scan_forex,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
