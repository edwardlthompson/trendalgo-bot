"""Tests for bot equity limits and chart regions."""

from __future__ import annotations

from trendalgo.bots.chart_regions import trade_highlight_regions
from trendalgo.bots.equity_limits import normalize_equity_mode, validate_equity_input


class _PaperState:
    class bot:
        dry_run = True


def test_normalize_equity_mode_legacy_values() -> None:
    assert normalize_equity_mode("usd") == "quote"
    assert normalize_equity_mode("pct") == "portfolio_pct"
    assert normalize_equity_mode("base") == "base"


def test_validate_portfolio_pct_cap() -> None:
    try:
        validate_equity_input(_PaperState(), "BTC/USD", "portfolio_pct", 101, paper=True)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "100" in str(exc)


def test_trade_highlight_regions_pairs_buy_sell() -> None:
    candles = [
        {"time": 1, "close": 100.0},
        {"time": 2, "close": 105.0},
        {"time": 3, "close": 102.0},
    ]
    markers = [
        {"time": 1, "side": "buy"},
        {"time": 3, "side": "sell", "pnl_usd": 2.0},
    ]
    regions = trade_highlight_regions(markers, candles)
    assert len(regions) == 1
    assert regions[0]["time_start"] == 1
    assert regions[0]["time_end"] == 3
    assert regions[0]["profitable"] is True
