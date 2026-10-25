"""MarketContext aggregate + regime / risk helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.analytics.indicator_consensus import compute_consensus
from trendalgo.analytics.market_context import MarketContext, compute_market_context
from trendalgo.analytics.market_regime_labels import user_regime_label
from trendalgo.analytics.market_risk import compute_risk


def _frame(n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    closes = 100 + np.cumsum(rng.normal(0, 0.4, n))
    return pd.DataFrame(
        {
            "close": closes,
            "high": closes + 0.8,
            "low": closes - 0.8,
            "volume": rng.uniform(100, 500, n),
        }
    )


def test_consensus_short_history_neutral() -> None:
    closes = np.linspace(100, 101, 10)
    result = compute_consensus(closes + 1, closes - 1, closes)
    assert result.signal == "Neutral"
    assert result.confidence == 0.0


def test_regime_labels() -> None:
    assert (
        user_regime_label(structural="trending", direction="up", volatility="normal", squeeze=False)
        == "Trending Up"
    )
    assert (
        user_regime_label(
            structural="trending", direction="down", volatility="normal", squeeze=False
        )
        == "Trending Down"
    )
    assert (
        user_regime_label(structural="ranging", direction="flat", volatility="low", squeeze=True)
        == "Compressing"
    )
    assert (
        user_regime_label(structural="choppy", direction="flat", volatility="high", squeeze=False)
        == "Volatile"
    )


def test_rr_math() -> None:
    risk = compute_risk(100.0, 2.0, r1=106.0, r2=109.0, stop_mult=1.5)
    # stop = 100 - 3 = 97; risk=3; R1 reward=6 → RR=2
    assert risk.stop == 97.0
    assert risk.rr_to_r1 == 2.0
    assert risk.rr_to_r2 == 3.0


def test_compute_market_context_ok() -> None:
    ctx = compute_market_context(_frame())
    assert ctx.ok
    assert ctx.last_price is not None
    assert ctx.consensus is not None
    assert ctx.regime_label
    assert ctx.risk is not None
    assert ctx.structure is not None
    assert ctx.structure.get("volume_ok") is True


def test_compute_market_context_empty() -> None:
    ctx = compute_market_context(None)
    assert not ctx.ok
    assert ctx.error == "no_candles"


def test_from_dict_roundtrip() -> None:
    ctx = compute_market_context(_frame())
    again = MarketContext.from_dict(ctx.to_dict())
    assert again.ok
    assert again.regime_label == ctx.regime_label
