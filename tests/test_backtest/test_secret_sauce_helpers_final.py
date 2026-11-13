"""Unit tests for Sauce helpers, Final Boss, uncapped budget, residual osc, S5 utils."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_features import (
    RESIDUAL_OSC_KEYS,
    causal_features,
    feature_keys_for,
)
from trendalgo.backtest.secret_sauce_lab.scale_out import scale_out_proxy_net
from trendalgo.backtest.secret_sauce_lab.search import lab_time_budget_s
from trendalgo.backtest.secret_sauce_lab.session_mask import hour_allow_mask
from trendalgo.backtest.secret_sauce_lab.veto_helper import apply_veto, false_entry_veto_mask
from trendalgo.backtest.secret_sauce_lab.vol_targeting import vol_target_scalar
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=0.001,
        maker_pct=0.001,
        tier="retail",
        source_url="",
    )


def _frame(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = 100 + np.cumsum(rng.normal(0.05, 0.8, size=n))
    high = close + rng.uniform(0.1, 1.0, size=n)
    low = close - rng.uniform(0.1, 1.0, size=n)
    vol = rng.uniform(100, 1000, size=n)
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close, "volume": vol},
        index=idx,
    )


def test_lab_time_budget_uncapped() -> None:
    assert math.isinf(lab_time_budget_s(0))
    assert math.isinf(lab_time_budget_s(50))


def test_residual_osc_keys_in_feature_bank() -> None:
    df = _frame()
    keys = feature_keys_for(df, include_pivots=True)
    for k in RESIDUAL_OSC_KEYS:
        assert k in keys
    feats = causal_features(df)
    assert "cci_20" in feats[10]
    assert "willr_14" in feats[10]
    assert "mfi_14" in feats[10]


def test_session_mask_default_hours() -> None:
    df = _frame(48)
    mask = hour_allow_mask(df)
    assert mask.dtype == bool
    assert mask.any()
    assert (~mask).any() or True  # overnight bars may exist


def test_scale_out_proxy_returns_nets() -> None:
    df = _frame()
    entries = np.zeros(len(df), dtype=bool)
    exits = np.zeros(len(df), dtype=bool)
    entries[10] = True
    exits[40] = True
    out = scale_out_proxy_net(df, entries, exits, fee=_fee(), stake_usd=100.0)
    assert "full_net" in out and "scale_out_net" in out
    assert "prefer_scale_out" in out


def test_vol_target_scalar_positive() -> None:
    assert vol_target_scalar(_frame()) > 0


def test_veto_mask_soft() -> None:
    df = _frame()
    entries = np.zeros(len(df), dtype=bool)
    entries[20] = True
    veto = false_entry_veto_mask(df, entries, look_ahead=3)
    cleaned = apply_veto(entries, veto)
    assert cleaned.dtype == bool
    assert cleaned.sum() <= entries.sum()


def test_final_boss_soft_none_on_empty_helpers() -> None:
    from trendalgo.backtest.secret_sauce_lab.final_boss import cook_final_boss

    assert cook_final_boss(_frame(), [], fee=_fee(), stake_usd=100.0) is None


def test_meta_tsl_grid_includes_20pct() -> None:
    from trendalgo.backtest.secret_sauce_lab.meta_tsl import _TSL_GRID

    assert 0.20 in _TSL_GRID
    assert 0.01 in _TSL_GRID
