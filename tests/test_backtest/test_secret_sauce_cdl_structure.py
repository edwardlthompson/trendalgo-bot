"""CDL + Fib/structure causal bank for Secret Sauce."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.secret_sauce_cdl import cdl_feature_keys, merge_cdl_into_rows
from trendalgo.backtest.secret_sauce_features import causal_features, feature_keys_for
from trendalgo.backtest.secret_sauce_structure import STRUCTURE_KEYS, merge_structure_into_rows


def _frame(n: int = 90) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    close = 25.0 + np.cumsum(rng.normal(0, 0.6, size=n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 30.0),
        }
    )


def test_cdl_feature_keys_include_q_beaters() -> None:
    keys = cdl_feature_keys()
    assert "cdl_cdldojistar" in keys
    assert "cdl_cdltakuri" in keys
    assert "cdl_cdlsidegap3methods" in keys


def test_merge_structure_writes_fib_and_momentum() -> None:
    df = _frame()
    closes = df["close"].to_numpy(dtype=float)
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    rows = [{} for _ in range(len(df))]
    merge_structure_into_rows(closes, highs, lows, rows)
    mid = rows[40]
    for key in STRUCTURE_KEYS:
        assert key in mid
    assert isinstance(mid["fib_dist_618"], float)
    assert mid["ema_xup_20_50"] in {0.0, 1.0}


def test_merge_cdl_soft_skips_or_writes_binary() -> None:
    df = _frame()
    rows = [{} for _ in range(len(df))]
    merge_cdl_into_rows(df, rows)
    # Soft-skip when TA-Lib missing is OK; when present values are 0/1.
    for row in rows:
        for key, val in row.items():
            assert key.startswith("cdl_")
            assert val in {0.0, 1.0}


def test_merge_cdl_with_mocked_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    import trendalgo.backtest.secret_sauce_cdl as cdl_mod

    df = _frame(40)
    fires = np.zeros(len(df), dtype=float)
    fires[10] = 100.0
    fires[20] = -100.0

    def _fake_compute(name: str, _df: pd.DataFrame, **_kwargs: object) -> dict[str, np.ndarray]:
        if name == "CDLDOJISTAR":
            return {"integer": fires}
        raise KeyError(name)

    monkeypatch.setattr(cdl_mod, "compute", _fake_compute, raising=False)
    # compute is imported inside merge_cdl_into_rows — patch engine module.
    monkeypatch.setattr("trendalgo.ta.engine.compute", _fake_compute)
    rows = [{} for _ in range(len(df))]
    merge_cdl_into_rows(df, rows)
    assert rows[10].get("cdl_cdldojistar") == 1.0
    assert rows[11].get("cdl_cdldojistar") == 0.0
    assert rows[20].get("cdl_cdldojistar") == 1.0


def test_causal_features_exposes_structure_and_cdl_keys() -> None:
    df = _frame()
    keys = feature_keys_for(df)
    assert "fib_touch_618" in keys
    assert "mom_10" in keys
    assert any(k.startswith("cdl_") for k in keys)
    feats = causal_features(df)
    assert "fib_dist_500" in feats[50]
    assert "roc_10" in feats[50]
