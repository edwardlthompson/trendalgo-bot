"""Universal TA signal generation for OHLCV backtests."""

from __future__ import annotations

import pandas as pd
import pytest

from trendalgo.strategies.runtime.contract import Candle
from trendalgo.ta.pandas_ta_catalog import pandas_ta_available
from trendalgo.ta.signals import resolve_preset, signals_for_preset
from trendalgo.ta.sweep import _candles_to_df

pytestmark = pytest.mark.skipif(
    not pandas_ta_available(),
    reason="pandas-ta-classic required for extended indicator signal tests",
)


def _fixture_df(rows: int = 120) -> pd.DataFrame:
    candles = [
        Candle(
            timestamp_ms=i * 3_600_000,
            open=100 + i * 0.05,
            high=101 + i * 0.05,
            low=99 + i * 0.05,
            close=100.5 + i * 0.05,
            volume=1000 + i,
        )
        for i in range(rows)
    ]
    return _candles_to_df(candles)


def test_vfi_zero_cross_signals() -> None:
    df = _fixture_df()
    preset = resolve_preset("VFI", {"length": 20})
    entries, exits = signals_for_preset(df, preset)
    assert len(entries) == len(df)
    assert entries.dtype == bool


def test_supertrend_price_cross_signals() -> None:
    df = _fixture_df()
    preset = resolve_preset("SUPERTREND", {"length": 7})
    entries, exits = signals_for_preset(df, preset)
    assert len(entries) == len(df)


def test_resolve_preset_for_extended_indicator() -> None:
    preset = resolve_preset("ALMA", {"length": 10})
    assert preset["fn"] == "ALMA"
    assert preset["kind"] in {"price_cross", "zero_cross", "bounded_reversal", "ma_cross"}


def test_all_strategies_emit_backtest_signals() -> None:
    from trendalgo.ta.catalog import all_ta_names

    df = _fixture_df(200)
    failures: list[str] = []
    for name in all_ta_names():
        preset = resolve_preset(name, {})
        try:
            entries, exits = signals_for_preset(df, preset)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
            continue
        if len(entries) != len(df) or len(exits) != len(df):
            failures.append(f"{name}: signal length mismatch")
    assert not failures, "backtest signal failures:\n" + "\n".join(failures[:20])
