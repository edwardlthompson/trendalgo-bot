"""prepare_signals treats indicator compute crashes as compute_error."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.ta_fleet import backtest_one, prepare_signals
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _frame(n: int = 80) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = pd.Series([100.0 + (i % 7) for i in range(n)], index=idx)
    return pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0},
        index=idx,
    )


def test_prepare_signals_swallows_index_error(monkeypatch: Any) -> None:
    def boom(*_a: Any, **_k: Any) -> tuple[Any, Any]:
        raise IndexError("iloc cannot enlarge its target object")

    monkeypatch.setattr("trendalgo.backtest.ta_fleet.signals_for_preset", boom)
    monkeypatch.setattr("trendalgo.backtest.ta_fleet.pandas_ta_available", lambda: True)
    entries, exits, err = prepare_signals(_frame(), "QQE")
    assert entries is None and exits is None and err == "compute_error"


def test_prepare_signals_missing_pandas_ta_backend(monkeypatch: Any) -> None:
    monkeypatch.setattr("trendalgo.backtest.ta_fleet.pandas_ta_available", lambda: False)
    monkeypatch.setattr("trendalgo.backtest.ta_fleet.is_pandas_ta_indicator", lambda _s: True)
    entries, exits, err = prepare_signals(_frame(), "HMA")
    assert entries is None and exits is None and err == "missing_backend"


def test_backtest_one_qqe_short_frame_does_not_raise() -> None:
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    # Undersized / awkward length that historically tripped pandas_ta QQE.
    row, reason = backtest_one(
        _frame(40),
        "QQE",
        fee,
        1000.0,
        timeframe="11h",
        lookback_seconds=0,
        trailing_stop_pct=0.01,
    )
    assert row is None
    assert reason in {"compute_error", "insufficient_bars", "no_trades", "missing_backend"}
