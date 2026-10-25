"""Persist / restore last Backtest-tab result."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.last_pair_backtest import (
    has_tradable_results,
    load_last_pair_backtest,
    save_last_pair_backtest,
)
from trendalgo.device.profile import write_json


def test_save_and_load_last_pair_backtest(tmp_path: Path) -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 12.0, "timeframe": "1h"},
        {"indicator": "B&H", "net_pct": 3.0, "timeframe": "1h"},
    ]
    save_last_pair_backtest(
        tmp_path, "eth/usd", rows, market_context={"ok": True, "regime_label": "Ranging"}
    )
    loaded = load_last_pair_backtest(tmp_path)
    assert loaded is not None
    pair, out, ctx = loaded
    assert pair == "ETH/USD"
    assert len(out) == 2
    assert out[0]["indicator"] == "RSI"
    assert ctx is not None and ctx.get("regime_label") == "Ranging"


def test_load_missing_or_empty_returns_none(tmp_path: Path) -> None:
    assert load_last_pair_backtest(tmp_path) is None
    save_last_pair_backtest(tmp_path, "BTC/USD", [])
    assert load_last_pair_backtest(tmp_path) is None


def test_skip_placeholders_are_not_persisted_or_restored(tmp_path: Path) -> None:
    placeholders = [
        {
            "indicator": "RSI",
            "net_pct": 0.0,
            "trades": 0,
            "timeframe": "—",
            "skip_reason": "insufficient_bars",
        }
    ]
    assert not has_tradable_results(placeholders)
    save_last_pair_backtest(tmp_path, "BTC/USD", placeholders)
    assert load_last_pair_backtest(tmp_path) is None
    write_json(
        tmp_path / "last_pair_backtest.json",
        {"pair": "BTC/USD", "rows": placeholders},
    )
    assert load_last_pair_backtest(tmp_path) is None
