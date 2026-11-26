"""Backtest surface export (AV-G6)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_export import load_backtest_surface


def test_load_backtest_surface(tmp_path: Path) -> None:
    (tmp_path / "last_pair_backtest.json").write_text(
        json.dumps(
            {
                "pair": "BTC/USD",
                "rows": [{"indicator": "RSI", "net_pct": 3.0}],
                "market_context": {"regime": "trend"},
            }
        ),
        encoding="utf-8",
    )
    data = load_backtest_surface(tmp_path)
    assert data["pair"] == "BTC/USD"
    assert data["rows"][0]["indicator"] == "RSI"
    assert data["market_context"]["regime"] == "trend"


def test_load_backtest_surface_summary_and_sort(tmp_path: Path) -> None:
    (tmp_path / "last_pair_backtest.json").write_text(
        json.dumps(
            {
                "pair": "ETH/USD",
                "rows": [
                    {"indicator": "AD", "net_pct": -1.5, "trades": 4, "wins": 1},
                    {"indicator": "Oracle max", "net_pct": 72.1, "trades": 10, "wins": 10},
                    {"indicator": "MACD", "net_pct": 14.2, "trades": 6, "wins": 4},
                ],
                "market_context": {
                    "last_price": 2000.0,
                    "consensus": {"signal": "Buy", "score": 0.65, "confidence": 72.0},
                    "pivots": {
                        "levels": [
                            {"name": "S1", "price": 1950.0, "strength": 2},
                            {"name": "R1", "price": 2100.0, "strength": 3},
                        ]
                    },
                    "risk": {"rr_to_r1": 2.0, "rr_to_r2": 3.5},
                    "structure": {
                        "vwap_dist_pct": 1.2,
                        "drawdown_from_high_pct": -3.4,
                        "poc": 1980.0,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    data = load_backtest_surface(tmp_path)
    assert [r["indicator"] for r in data["rows"]] == ["Oracle max", "MACD", "AD"]
    summary = data["market_context_summary"]
    assert set(summary) == {"signal", "levels", "risk", "structure"}
    assert "Buy" in summary["signal"]
    assert "R1" in summary["levels"]
    assert summary["risk"]
    assert summary["structure"]
