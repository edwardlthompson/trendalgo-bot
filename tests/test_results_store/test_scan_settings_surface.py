"""scan_settings surface — TF/strategy checklist apply."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.scan_bt_prefs import ScanBtPrefs, load_scan_bt_prefs, save_scan_bt_prefs
from trendalgo.results_store.scan_settings_surface import apply_scan_settings, scan_settings_view


def test_view_lists_catalog(tmp_path: Path) -> None:
    save_scan_bt_prefs(tmp_path, ScanBtPrefs(timeframes=["1h", "4h"], strategy_denylist=["RSI"]))
    view = scan_settings_view(tmp_path)
    tfs = {row["id"]: row["enabled"] for row in view["timeframes"]}
    assert tfs["1h"] is True
    assert tfs["4h"] is True
    assert tfs["1m"] is False
    strats = {row["id"]: row["enabled"] for row in view["strategies"]}
    assert strats["RSI"] is False
    assert view["enabled_tf_count"] == 2


def test_apply_updates_denylist(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    for row in view["timeframes"]:
        row["enabled"] = row["id"] in {"1h", "2h"}
    for row in view["strategies"]:
        row["enabled"] = row["id"] != "ADX"
    view["sauce_top_n"] = 12
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is True
    prefs = load_scan_bt_prefs(tmp_path)
    assert set(prefs.timeframes) == {"1h", "2h"}
    assert "ADX" in prefs.strategy_denylist
    assert prefs.sauce_top_n == 12


def test_apply_refuses_empty_tfs(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    for row in view["timeframes"]:
        row["enabled"] = False
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is False
    assert result["error"] == "empty_timeframes"


def test_view_exposes_tf_bands_and_mix_note(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    assert view["bands_mix_ready"] is False
    assert "mix" in view["subhour_mix_note"].lower() or "Cannot mix" in view["subhour_mix_note"]
    band_ids = [b["id"] for b in view["tf_bands"]]
    assert band_ids == ["subhour", "hours"]
    assert "1m" in view["tf_bands"][0]["timeframes"]
    assert "1h" in view["tf_bands"][1]["timeframes"]


def test_results_view_prefs_round_trip(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    for row in view["timeframes"]:
        row["enabled"] = row["id"] == "1h"
    view["results_view"] = {"heatmap_enabled": True, "perfect_only": True}
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is True
    from trendalgo.device.results_view_prefs import load_results_prefs

    prefs = load_results_prefs(tmp_path)
    assert prefs.heatmap_enabled is True
    assert prefs.perfect_only is True


def test_lane_prefs_and_tradfi_filters_round_trip(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    assert "lane_prefs" in view
    assert "tradfi" in view["lane_scan_filters"]
    for row in view["timeframes"]:
        row["enabled"] = row["id"] == "1h"
    view["lane_prefs"] = {
        "auto_scan_crypto": False,
        "auto_scan_tradfi": True,
        "auto_scan_forex": True,
    }
    view["lane_scan_filters"] = {
        "tradfi": {
            "min_abs_gain_pct": 9.0,
            "min_range_pct": 11.0,
            "top_n": 77,
            "min_adv_usd": 0,
            "min_price": 2.5,
        }
    }
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is True
    from trendalgo.device.lane_prefs import load_lane_prefs
    from trendalgo.device.lane_scan_filters import load_lane_scan_filters

    prefs = load_lane_prefs(tmp_path)
    assert prefs.auto_scan_crypto is False
    assert prefs.auto_scan_tradfi is True
    filt = load_lane_scan_filters(tmp_path, "tradfi")
    assert filt.min_abs_gain_pct == 9.0
    assert filt.top_n == 77


def test_extras_flags_round_trip(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    for row in view["timeframes"]:
        row["enabled"] = row["id"] == "1h"
    view["market_context_with_scan"] = False
    view["sauce_with_scan"] = True
    view["sauce_top_n"] = 7
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is True
    prefs = load_scan_bt_prefs(tmp_path)
    assert prefs.market_context_with_scan is False
    assert prefs.sauce_with_scan is True
    assert prefs.sauce_top_n == 7


def test_view_exposes_eta_header(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    eta = view["eta"]
    assert eta["title"]
    assert len(eta["lines"]) == 3
    assert "Grand total" in eta["total"]


def test_apply_persists_ohlcvt_path(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    for row in view["timeframes"]:
        row["enabled"] = row["id"] == "1h"
    view["ohlcvt_path"] = str(tmp_path / "Kraken_OHLCVT_Full.zip")
    view["ohlcvt_auto_tip"] = True
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is True
    prefs = load_scan_bt_prefs(tmp_path)
    assert prefs.ohlcvt_auto_tip is True
    assert "Kraken_OHLCVT_Full.zip" in prefs.ohlcvt_path


def test_apply_exclusive_bands_when_mix_not_ready(tmp_path: Path) -> None:
    view = scan_settings_view(tmp_path)
    assert view["bands_mix_ready"] is False
    for row in view["timeframes"]:
        row["enabled"] = row["id"] in {"5m", "1h"}
    result = apply_scan_settings(tmp_path, view)
    assert result["ok"] is True
    prefs = load_scan_bt_prefs(tmp_path)
    assert "5m" not in prefs.timeframes
    assert "1h" in prefs.timeframes
