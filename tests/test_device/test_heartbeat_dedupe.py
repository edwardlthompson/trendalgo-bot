"""Backtest dedupe + export params + TSL floor."""

from __future__ import annotations

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES
from trendalgo.backtest.hill_climb import MIN_TSL
from trendalgo.backtest.hill_climb_axes import seed_params
from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import HEAT_COLS, format_export_params
from trendalgo.device.pair_strategy_scan import dedupe_indicator_tf


def test_heartbeat_timeframes_1_to_24() -> None:
    assert HEARTBEAT_TIMEFRAMES[0] == "1h"
    assert HEARTBEAT_TIMEFRAMES[-1] == "24h"
    assert len(HEARTBEAT_TIMEFRAMES) == 24


def test_dedupe_keeps_best_per_indicator() -> None:
    rows = [
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "net_pct": 1.0,
            "optimized": False,
            "win_pct": 40.0,
            "tsl_hits": 0,
        },
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "net_pct": 5.0,
            "optimized": True,
            "win_pct": 50.0,
            "tsl_hits": 1,
        },
        {
            "indicator": "RSI",
            "timeframe": "2h",
            "net_pct": 2.0,
            "optimized": False,
            "win_pct": 40.0,
            "tsl_hits": 0,
        },
        {"indicator": "B&H", "timeframe": "1h", "net_pct": 1.0},
        {"indicator": "B&H", "timeframe": "2h", "net_pct": 3.0},
    ]
    out = dedupe_indicator_tf(rows)
    rsi = [r for r in out if r["indicator"] == "RSI"]
    assert len(rsi) == 1
    assert rsi[0]["net_pct"] == 5.0
    assert rsi[0]["timeframe"] == "1h"
    assert rsi[0]["optimized"] is True
    assert sum(1 for r in out if r["indicator"] == "B&H") == 1
    assert next(r for r in out if r["indicator"] == "B&H")["net_pct"] == 3.0


def test_export_params_includes_tsl_and_ints() -> None:
    text = format_export_params(
        {
            "params": {"timeperiod": 14.2, "entry_level": 25.0, "exit_level": 72.4},
            "trailing_stop_pct": 0.03,
        }
    )
    assert "timeperiod=14" in text
    assert "entry_level=25" in text
    assert "exit_level=72" in text
    assert "tsl=3%" in text


def test_seed_params_are_integers() -> None:
    params = seed_params("RSI", {"timeperiod": 14.7, "entry_level": 30.2})
    assert all(isinstance(v, int) for v in params.values())
    assert params["timeperiod"] == 15
    assert MIN_TSL == 0.01


def test_scanner_headers_match_backtest() -> None:
    assert S.BACKTEST_RESULT_HEADERS[3] == "Net %"
    assert S.BACKTEST_RESULT_HEADERS[4] == "Fees $"
    assert S.BACKTEST_RESULT_HEADERS[5] == "Open"
    assert S.BACKTEST_RESULT_HEADERS[6] == "Wins"
    assert S.BACKTEST_RESULT_HEADERS[7] == "Losses"
    assert HEAT_COLS[4] == ("fees_paid", True)
    assert HEAT_COLS[5] == ("open_trades", True)
    assert HEAT_COLS[6] == ("wins", False)
    assert HEAT_COLS[7] == ("losses", True)
    assert HEAT_COLS[10] == ("tsl_hits", True)
