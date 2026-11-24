"""AV-G-SET2 — lanes auto-scan surface + apply."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.lane_prefs import load_lane_prefs
from trendalgo.results_store.desk_lanes import apply_lanes_settings, load_lanes_surface


def test_lanes_surface_defaults(tmp_path: Path) -> None:
    data = load_lanes_surface(tmp_path)
    assert data["auto_scan_crypto"] is True
    assert data["auto_scan_tradfi"] is False
    assert data["auto_scan_forex"] is False
    assert data["alpaca_hint"]
    assert data["hint"]
    assert {row["id"] for row in data["lanes"]} == {"crypto", "tradfi", "forex"}


def test_apply_lanes_settings(tmp_path: Path) -> None:
    result = apply_lanes_settings(
        tmp_path,
        {"auto_scan_crypto": False, "auto_scan_tradfi": True, "auto_scan_forex": True},
    )
    assert result["ok"] is True
    prefs = load_lane_prefs(tmp_path)
    assert prefs.auto_scan_crypto is False
    assert prefs.auto_scan_tradfi is True
    assert prefs.auto_scan_forex is True
