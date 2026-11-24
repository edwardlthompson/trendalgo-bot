"""Settings → Lanes: auto-scan toggles + Alpaca hint (AV-G-SET2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["apply_lanes_settings", "load_lanes_surface"]


def load_lanes_surface(root: Path) -> dict[str, Any]:
    from trendalgo.device import strings as S
    from trendalgo.device.alpaca_vault import has_alpaca_credentials
    from trendalgo.device.lane_prefs import load_lane_prefs

    prefs = load_lane_prefs(root)
    keyed = False
    try:
        keyed = has_alpaca_credentials()
    except Exception:
        keyed = False
    return {
        "hint": S.LANES_SETTINGS_HINT,
        "alpaca_hint": S.LANES_ALPACA_HINT,
        "alpaca_wizard_label": S.NOTIFY_ALPACA_WIZARD,
        "alpaca_keyed": keyed,
        "lanes": [
            {
                "id": "crypto",
                "label": "Crypto",
                "auto_scan": prefs.auto_scan_crypto,
                "needs_alpaca": False,
            },
            {
                "id": "tradfi",
                "label": "TradFi",
                "auto_scan": prefs.auto_scan_tradfi,
                "needs_alpaca": True,
            },
            {
                "id": "forex",
                "label": "Forex",
                "auto_scan": prefs.auto_scan_forex,
                "needs_alpaca": True,
            },
        ],
        "auto_scan_crypto": prefs.auto_scan_crypto,
        "auto_scan_tradfi": prefs.auto_scan_tradfi,
        "auto_scan_forex": prefs.auto_scan_forex,
    }


def apply_lanes_settings(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    from trendalgo.device.lane_prefs import LanePrefs, load_lane_prefs, save_lane_prefs

    cur = load_lane_prefs(root)
    prefs = LanePrefs(
        auto_scan_crypto=bool(payload.get("auto_scan_crypto", cur.auto_scan_crypto)),
        auto_scan_tradfi=bool(payload.get("auto_scan_tradfi", cur.auto_scan_tradfi)),
        auto_scan_forex=bool(payload.get("auto_scan_forex", cur.auto_scan_forex)),
    )
    save_lane_prefs(root, prefs)
    return {
        "ok": True,
        "auto_scan_crypto": prefs.auto_scan_crypto,
        "auto_scan_tradfi": prefs.auto_scan_tradfi,
        "auto_scan_forex": prefs.auto_scan_forex,
    }
