"""Exact signal parity tests for fast-path pandas-ta indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.ta import fast_pta_indicators as fpi
from trendalgo.ta.signals import resolve_preset, signals_for_preset


def _sample_df(n: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(123)
    c = 100.0 + np.cumsum(rng.normal(0.0, 1.2, n))
    o = c + rng.normal(0.0, 0.4, n)
    h = np.maximum(o, c) + rng.uniform(0.1, 1.0, n)
    lo = np.minimum(o, c) - rng.uniform(0.1, 1.0, n)
    v = rng.uniform(100.0, 5000.0, n)
    return pd.DataFrame({"open": o, "high": h, "low": lo, "close": c, "volume": v}, index=idx)


@pytest.mark.parametrize("sid", ["PSAR", "HILO", "HWC", "HWMA", "QQE", "LRSI", "FISHER", "JMA"])
def test_fast_pta_matches_pandas_ta_signals(monkeypatch: pytest.MonkeyPatch, sid: str) -> None:
    df = _sample_df()
    preset = resolve_preset(sid)
    en_fast, ex_fast = signals_for_preset(df, preset)

    monkeypatch.setattr("trendalgo.ta.pandas_ta_engine.compute_fast_pta", lambda *_a, **_k: None)
    en_ref, ex_ref = signals_for_preset(df, preset)
    assert np.array_equal(en_fast, en_ref), f"{sid} entries mismatch"
    assert np.array_equal(ex_fast, ex_ref), f"{sid} exits mismatch"
    assert fpi.compute_fast_pta(sid, df, {}) is not None
