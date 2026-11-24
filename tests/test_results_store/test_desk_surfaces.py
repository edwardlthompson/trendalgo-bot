"""Desk surface exports for Avalonia Results/DEX/events (AV-G4)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_surfaces import (
    chart_summary_from_coin,
    load_dex_surface,
    strategy_sheet_from_coin,
)


def test_strategy_sheet_ranks_and_appends_bh_oracle() -> None:
    coin = {
        "pair": "BTC/USD",
        "backtest_top_strategies": [
            {"indicator": "RSI", "net_pct": 1.0},
            {"indicator": "MACD", "net_pct": 5.0},
        ],
        "backtest_buy_hold": {"indicator": "B&H", "net_pct": 2.0},
        "backtest_oracle_max": {"indicator": "Oracle max", "net_pct": 9.0},
    }
    rows = strategy_sheet_from_coin(coin)
    names = [r["indicator"] for r in rows]
    assert names[0] == "Oracle max"
    assert "MACD" in names
    assert "B&H" in names


def test_load_dex_surface(tmp_path: Path) -> None:
    (tmp_path / "dex_watch_rows.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair": "PEPE/WETH",
                        "liquidity_usd": 1e6,
                        "price_change_24h_pct": 3.2,
                        "source": "uniswap",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rows = load_dex_surface(tmp_path)
    assert len(rows) == 1
    assert rows[0]["pair"] == "PEPE/WETH"


def test_chart_summary_from_closes() -> None:
    coin = {"pair": "ETH/USD", "chart_closes": [1.0, 2.0, 1.5]}
    summary = chart_summary_from_coin(coin)
    assert summary["pair"] == "ETH/USD"
    assert summary["bars"] == 3
    assert summary["last"] == 1.5
    assert summary["high"] == 2.0
    assert summary["low"] == 1.0
    assert abs(float(summary["change_pct"]) - 50.0) < 1e-9
    assert len(summary["candles"]) == 3
    assert summary["candles"][-1]["close"] == 1.5


def test_chart_summary_includes_ohlc_and_trades() -> None:
    coin = {
        "pair": "BTC/USD",
        "chart_ohlc_1h": [
            {"t": 1, "o": 1.0, "h": 1.2, "l": 0.9, "c": 1.1},
            {"t": 2, "o": 1.1, "h": 1.3, "l": 1.0, "c": 1.2},
        ],
        "backtest_top_strategies": [
            {
                "indicator": "RSI",
                "trades": [
                    {
                        "entry_time": "2024-01-01T00:00:00Z",
                        "entry_price": 1.05,
                        "exit_time": "2024-01-02T00:00:00Z",
                        "exit_price": 1.15,
                    }
                ],
            }
        ],
    }
    summary = chart_summary_from_coin(coin)
    assert len(summary["ohlc"]) == 2
    assert summary["ohlc"][0]["o"] == 1.0
    assert len(summary["trades"]) == 2
    assert summary["trades"][0]["side"] == "entry"
