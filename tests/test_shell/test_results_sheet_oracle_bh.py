"""AV-G-RES1 — strategy sheet keeps Oracle max + B&H rows."""

from __future__ import annotations

from trendalgo.results_store.desk_surfaces import strategy_sheet_from_coin


def test_strategy_sheet_appends_oracle_and_bh() -> None:
    coin = {
        "backtest_top_strategies": [
            {"indicator": "RSI", "net_pct": 12.0, "timeframe": "1h"},
            {"indicator": "MACD", "net_pct": 8.0, "timeframe": "1h"},
        ],
        "backtest_buy_hold": {"net_pct": 5.0, "timeframe": "1h"},
        "backtest_oracle_max": {"net_pct": 40.0, "timeframe": "1h"},
    }
    rows = strategy_sheet_from_coin(coin)
    names = [str(r.get("indicator") or "") for r in rows]
    assert "RSI" in names
    assert "B&H" in names
    assert "Oracle max" in names
