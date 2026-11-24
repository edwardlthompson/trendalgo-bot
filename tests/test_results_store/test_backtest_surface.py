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
