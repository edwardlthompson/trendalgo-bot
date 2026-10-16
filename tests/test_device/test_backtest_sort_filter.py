"""Backtest column sort + filters (TSL Hits=0, Win %)."""

from __future__ import annotations

from trendalgo.device.backtest_row_filter import filter_rows
from trendalgo.device.backtest_sort import sort_rows


def _row(
    ind: str,
    *,
    net: float,
    trades: int,
    win: float,
    hits: int,
    tf: str = "1h",
) -> dict:
    return {
        "indicator": ind,
        "timeframe": tf,
        "params": {"timeperiod": 14},
        "net_pct": net,
        "fees_paid": 1.0,
        "trades": trades,
        "win_pct": win,
        "trailing_stop_pct": 2.0,
        "tsl_hits": hits,
    }


def test_sort_by_tsl_hits_asc() -> None:
    rows = [
        _row("A", net=1, trades=10, win=50, hits=5),
        _row("B", net=2, trades=10, win=50, hits=0),
        _row("C", net=3, trades=10, win=50, hits=2),
    ]
    out = sort_rows(rows, key="tsl_hits", direction=1)
    assert [r["indicator"] for r in out] == ["B", "C", "A"]


def test_filter_zero_tsl_hits_and_min_win() -> None:
    rows = [
        _row("clean", net=5, trades=12, win=100, hits=0),
        _row("noisy", net=8, trades=12, win=90, hits=4),
        _row("weak", net=2, trades=3, win=40, hits=0),
        {"indicator": "B&H", "net_pct": 1.0, "trades": "-", "win_pct": "-", "tsl_hits": 0},
    ]
    out = filter_rows(rows, {"max_tsl_hits": 0, "min_win_pct": 80})
    names = {r["indicator"] for r in out}
    assert names == {"clean", "B&H"}
