"""Stage-B signal winners → TSL deepen seed gate."""

from __future__ import annotations

from trendalgo.device.scanner_tsl_seeds import best_signal_per_strategy, select_tsl_seeds


def test_best_signal_keeps_best_tf_per_strategy() -> None:
    rows = [
        {"strategy_id": "RSI", "timeframe": "1h", "net_profit": 1.0, "trades": 4},
        {"strategy_id": "RSI", "timeframe": "4h", "net_profit": 5.0, "trades": 3},
        {"strategy_id": "MACD", "timeframe": "1h", "net_profit": 2.0, "trades": 6},
    ]
    out = best_signal_per_strategy(rows)
    by_id = {r["strategy_id"]: r for r in out}
    assert by_id["RSI"]["timeframe"] == "4h"
    assert by_id["MACD"]["timeframe"] == "1h"


def test_select_tsl_seeds_requires_min_trades() -> None:
    rows = [
        {"strategy_id": "A", "net_profit": 9.0, "trades": 2},
        {"strategy_id": "B", "net_profit": 3.0, "trades": 3},
        {"strategy_id": "C", "net_profit": 8.0, "trades": 10},
    ]
    seeds = select_tsl_seeds(rows, min_trades=3)
    assert [r["strategy_id"] for r in seeds] == ["C", "B"]
