"""Scanner Results → Plan prefill mapping."""

from __future__ import annotations

from trendalgo.device.scanner_plan_prefill import (
    integer_stop_pct,
    map_indicator_to_live,
    map_timeframe_to_plan,
    plan_prefill_from_scanner_row,
)


def test_map_catalog_indicators_to_live() -> None:
    assert map_indicator_to_live("RSI") == "RSI"
    assert map_indicator_to_live("EMA") == "EMA Crossover"
    assert map_indicator_to_live("BBANDS") == "Bollinger %B"
    assert map_indicator_to_live("EMA *") == "EMA Crossover"
    assert map_indicator_to_live("CDL2CROWS") is None


def test_map_timeframe_aliases() -> None:
    assert map_timeframe_to_plan("1h") == "1h"
    assert map_timeframe_to_plan("60") == "1h"
    assert map_timeframe_to_plan("240") == "4h"
    assert map_timeframe_to_plan("15m") is None


def test_integer_stop_pct_floor() -> None:
    assert integer_stop_pct(0) == "1"
    assert integer_stop_pct(0.05) == "5"
    assert integer_stop_pct(3.2) == "3"
    assert integer_stop_pct(None) == "1"


def test_plan_prefill_live_row() -> None:
    fields, note = plan_prefill_from_scanner_row(
        {"indicator": "RSI", "timeframe": "1h", "trailing_stop_pct": 2.0},
        pair="BTC/USD",
        stake_usd=100.0,
    )
    assert note == ""
    assert fields is not None
    assert fields["indicator"] == "RSI"
    assert fields["timeframe"] == "1h"
    assert fields["stop"] == "2"
    assert fields["pair"] == "BTC/USD"


def test_plan_prefill_unmapped_indicator() -> None:
    fields, note = plan_prefill_from_scanner_row(
        {"indicator": "CDLDOJI", "timeframe": "1h", "trailing_stop_pct": 1.0},
        pair="ETH/USD",
    )
    assert fields is not None
    assert fields["indicator"] == "CDLDOJI"  # catalog id kept for local save
    assert "not on the live host list" in note
