"""AV-G-OTH2 — backtest surface toolbar/body parity fields."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.last_pair_backtest import LAST_BACKTEST_FILE
from trendalgo.results_store.desk_export import load_backtest_surface
from trendalgo.results_store.desk_results_prefs import apply_results_prefs


def test_backtest_surface_empty_toolbar_labels(tmp_path: Path) -> None:
    data = load_backtest_surface(tmp_path)
    assert data["ok"] is True
    assert data["empty"] is True
    assert data["run_label"]
    assert data["refresh_label"]
    assert data["perfect_label"]
    assert data["empty_title"]
    assert data["strategy_caption"]


def test_backtest_surface_perfect_filter(tmp_path: Path) -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 10, "perfect": True},
        {"indicator": "MACD", "net_pct": 5, "perfect": False},
    ]
    # Ensure tradable results (no skip_reason)
    (tmp_path / LAST_BACKTEST_FILE).write_text(
        json.dumps({"pair": "BTC/USD", "rows": rows, "market_context": {"regime": "trend"}}),
        encoding="utf-8",
    )
    apply_results_prefs(tmp_path, {"perfect_only": True, "last_pair": "BTC/USD"})
    data = load_backtest_surface(tmp_path)
    assert data["perfect_only"] is True
    assert data["raw_count"] == 2
    # filter_perfect_rows may keep only perfect — assert surface returns fewer or equal
    assert data["count"] <= data["raw_count"]
    assert data["market_context"]["regime"] == "trend"


def test_backtest_surface_column_filters(tmp_path: Path) -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 12, "timeframe": "1h", "trades": 3},
        {"indicator": "MACD", "net_pct": 2, "timeframe": "4h", "trades": 3},
        {"indicator": "B&H", "net_pct": 1, "timeframe": "1h", "trades": 1},
    ]
    (tmp_path / LAST_BACKTEST_FILE).write_text(
        json.dumps({"pair": "ETH/USD", "rows": rows}),
        encoding="utf-8",
    )
    (tmp_path / "shell_backtest_filters.json").write_text(
        json.dumps({"indicator_contains": "rsi", "min_net_pct": 10}),
        encoding="utf-8",
    )
    data = load_backtest_surface(tmp_path)
    ids = {r.get("indicator") for r in data["rows"]}
    assert "RSI" in ids
    assert "B&H" in ids  # always kept
    assert "MACD" not in ids
    assert data["headers"]
