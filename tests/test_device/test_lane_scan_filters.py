"""TradFi/FX scan filter defaults, presets, helpers, and persist roundtrip."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.lane_scan_filters import (
    DEFAULT_MIN_ABS_GAIN_PCT,
    DEFAULT_MIN_ADV_USD,
    DEFAULT_MIN_PRICE,
    DEFAULT_MIN_RANGE_PCT,
    DEFAULT_TOP_N,
    TRADFI_MOVE_PRESETS,
    LaneScanFilters,
    abs_gain_pct,
    apply_preset,
    avg_dollar_volume,
    default_lane_scan_filters,
    load_lane_scan_filters,
    realized_range_pct,
    save_lane_scan_filters,
)
from trendalgo.market.types import OhlcvPoint


def test_balanced_defaults() -> None:
    tf = default_lane_scan_filters("tradfi")
    assert tf.min_adv_usd == DEFAULT_MIN_ADV_USD == 0.0
    assert tf.min_price == DEFAULT_MIN_PRICE == 0.0
    assert tf.min_abs_gain_pct == DEFAULT_MIN_ABS_GAIN_PCT == 5.0
    assert tf.min_range_pct == DEFAULT_MIN_RANGE_PCT == 8.0
    assert tf.top_n == DEFAULT_TOP_N == 120
    fx = default_lane_scan_filters("forex")
    assert fx == LaneScanFilters(0.0, 0.0, 0.0, 0.0, 0)


def test_presets_tradfi_move_keep_user_price() -> None:
    cur = LaneScanFilters(
        min_adv_usd=1.0, min_price=12.5, min_abs_gain_pct=1, min_range_pct=1, top_n=9
    )
    tight = apply_preset("tradfi", "tight", cur)
    assert (tight.min_abs_gain_pct, tight.min_range_pct, tight.top_n) == TRADFI_MOVE_PRESETS[
        "tight"
    ]
    assert tight.min_adv_usd == 0.0
    assert tight.min_price == 12.5
    wide = apply_preset("tradfi", "wide", cur)
    assert wide.top_n == 200
    assert wide.min_price == 12.5


def test_presets_forex_noop_filters() -> None:
    cur = LaneScanFilters(
        min_adv_usd=99.0, min_price=1.0, min_abs_gain_pct=5, min_range_pct=8, top_n=10
    )
    bal = apply_preset("forex", "balanced", cur)
    assert bal == LaneScanFilters(0.0, 0.0, 0.0, 0.0, 0)


def test_roundtrip_prefs_all_five_fields(tmp_path: Path) -> None:
    prefs = LaneScanFilters(
        min_adv_usd=0.0,
        min_price=2.5,
        min_abs_gain_pct=7.0,
        min_range_pct=11.0,
        top_n=90,
    )
    save_lane_scan_filters(tmp_path, "tradfi", prefs)
    loaded = load_lane_scan_filters(tmp_path, "tradfi")
    assert loaded.min_adv_usd == 0.0
    assert loaded.min_price == 2.5
    assert loaded.min_abs_gain_pct == 7.0
    assert loaded.min_range_pct == 11.0
    assert loaded.top_n == 90
    raw = (tmp_path / "lane_scan_filters.json").read_text(encoding="utf-8")
    assert "max_symbols" not in raw
    assert "min_abs_gain_pct" in raw


def test_roundtrip_ignores_stale_max(tmp_path: Path) -> None:
    path = tmp_path / "lane_scan_filters.json"
    path.write_text(
        '{"tradfi":{"min_adv_usd":0,"min_price":0,"min_abs_gain_pct":5,'
        '"min_range_pct":8,"top_n":120,"max_symbols":50}}',
        encoding="utf-8",
    )
    loaded = load_lane_scan_filters(tmp_path, "tradfi")
    assert loaded.top_n == 120
    assert "max_symbols" not in loaded.__dataclass_fields__


def test_avg_dollar_volume() -> None:
    pts = [
        OhlcvPoint(time=i, open=10, high=10, low=10, close=10, volume=1_000_000) for i in range(5)
    ]
    assert avg_dollar_volume(pts) == 10_000_000.0


def test_abs_gain_and_range_helpers() -> None:
    flat = [
        OhlcvPoint(time=i, open=100, high=100.1, low=99.9, close=100, volume=1) for i in range(22)
    ]
    assert abs_gain_pct(flat) < 1.0
    assert realized_range_pct(flat) < 1.0
    mover = [
        OhlcvPoint(
            time=i,
            open=100 + i,
            high=110 + i,
            low=90 + i,
            close=100 + i * 2,
            volume=1,
        )
        for i in range(22)
    ]
    assert abs_gain_pct(mover) > 5.0
    assert realized_range_pct(mover) > 8.0
