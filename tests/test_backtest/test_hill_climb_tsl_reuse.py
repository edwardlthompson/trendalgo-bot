"""TSL climb reuses prepare_signals once per param set."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.hill_climb_tsl import climb_tsl_grid
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def test_climb_tsl_calls_prepare_once(monkeypatch: Any) -> None:
    idx = pd.date_range("2024-01-01", periods=8, freq="h", tz="UTC")
    close = pd.Series([100, 100, 110, 105, 120, 115, 130, 100], index=idx, dtype=float)
    frame = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0},
        index=idx,
    )
    calls = {"n": 0}
    entries = np.array([False, True, False, False, False, False, False, False])
    exits = np.array([False, False, False, True, False, False, False, False])

    def fake_prepare(df: Any, sid: str, params: Any = None) -> Any:
        calls["n"] += 1
        return entries, exits, dict(params or {})

    monkeypatch.setattr("trendalgo.backtest.hill_climb_tsl.prepare_signals", fake_prepare)
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    seed = {
        "strategy_id": "RSI",
        "net_profit": 0.0,
        "params": {"timeperiod": 14},
        "trailing_stop_pct": 0.01,
        "timeframe": "1h",
    }
    out = climb_tsl_grid(
        frame,
        "RSI",
        {"timeperiod": 14},
        "1h",
        fee,
        1000.0,
        seed,
        0.0,
        trial_fn=lambda *_a, **_k: None,
    )
    assert calls["n"] == 1
    assert out is not None
    assert float(out.get("trailing_stop_pct") or 0) >= 0.01
