"""Lane Auto-scan prefs + migration + desk nav."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.lane_prefs import (
    LanePrefs,
    load_lane_prefs,
    save_lane_prefs,
)
from trendalgo.device.lane_symbol_sources import research_symbol_choices
from trendalgo.device.nav_layout import (
    BACKTESTS,
    FOREX,
    LEGACY_INT_TO_GLYPH,
    NAV_BY_GLYPH,
    PRIMARY_COUNT,
    PRIMARY_GLYPHS,
    SCANNER,
    TRADFI,
)
from trendalgo.device.profile import write_json
from trendalgo.device.ui_state import load_nav_page, save_nav_page, ui_state_path


def test_auto_scan_defaults() -> None:
    prefs = LanePrefs()
    assert prefs.auto_scan("crypto") is True
    assert prefs.auto_scan("tradfi") is False
    assert prefs.auto_scan("forex") is False


def test_prefs_round_trip(tmp_path: Path) -> None:
    prefs = LanePrefs(auto_scan_crypto=False, auto_scan_tradfi=True, auto_scan_forex=True)
    save_lane_prefs(tmp_path, prefs)
    loaded = load_lane_prefs(tmp_path)
    assert loaded == prefs
    raw = json.loads((tmp_path / "lane_prefs.json").read_text(encoding="utf-8"))
    assert "show_crypto" not in raw
    assert "hourly_tradfi" not in raw
    assert raw["auto_scan_tradfi"] is True


def test_migrate_show_keys(tmp_path: Path) -> None:
    (tmp_path / "lane_prefs.json").write_text(
        json.dumps({"show_crypto": True, "show_tradfi": True, "show_forex": False}),
        encoding="utf-8",
    )
    prefs = load_lane_prefs(tmp_path)
    assert prefs.auto_scan_crypto is True
    assert prefs.auto_scan_tradfi is True
    assert prefs.auto_scan_forex is False


def test_migrate_hourly_keys(tmp_path: Path) -> None:
    (tmp_path / "lane_prefs.json").write_text(
        json.dumps({"hourly_crypto": False, "hourly_tradfi": True, "hourly_forex": True}),
        encoding="utf-8",
    )
    prefs = load_lane_prefs(tmp_path)
    assert prefs.auto_scan_crypto is False
    assert prefs.auto_scan_tradfi is True
    assert prefs.auto_scan_forex is True
    save_lane_prefs(tmp_path, prefs)
    raw = json.loads((tmp_path / "lane_prefs.json").read_text(encoding="utf-8"))
    assert set(raw) == {"auto_scan_crypto", "auto_scan_tradfi", "auto_scan_forex"}


def test_nav_desk_indices() -> None:
    assert PRIMARY_COUNT == 7
    assert PRIMARY_GLYPHS == (
        "portfolio",
        "alerts",
        "scanner",
        "tradfi",
        "forex",
        "backtest",
        "bot",
    )
    assert NAV_BY_GLYPH["scanner"] == SCANNER
    assert NAV_BY_GLYPH["tradfi"] == TRADFI
    assert NAV_BY_GLYPH["forex"] == FOREX
    assert BACKTESTS == TRADFI + 2
    assert LEGACY_INT_TO_GLYPH[1] == "scanner"


def test_glyph_nav_restore_desks(tmp_path: Path) -> None:
    save_nav_page(tmp_path, TRADFI)
    assert load_nav_page(tmp_path) == TRADFI
    save_nav_page(tmp_path, FOREX)
    assert load_nav_page(tmp_path) == FOREX
    write_json(ui_state_path(tmp_path), {"nav_page": "tradfi"})
    assert load_nav_page(tmp_path) == TRADFI


def test_research_symbols_include_all_desks() -> None:
    choices = research_symbol_choices()
    assert "BTC/USD" in choices or any("/" in s for s in choices[:5])
    assert len(choices) > 100
