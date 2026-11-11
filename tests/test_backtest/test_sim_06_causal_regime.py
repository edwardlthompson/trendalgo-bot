"""SIM-06: per-bar causal regime weights; tip snapshot display-only."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_lab.regime_snapshot import (
    detect_regime,
    regime_weights_series,
)


def test_mid_history_regime_shift_changes_budgets() -> None:
    # Quiet range then strong uptrend.
    n = 160
    rng = np.random.default_rng(1)
    quiet = 100.0 + rng.normal(0, 0.2, size=80)
    trend = quiet[-1] + np.cumsum(rng.normal(0.4, 0.3, size=80))
    close = np.concatenate([quiet, trend])
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.ones(n) * 50,
        }
    )
    series = regime_weights_series(df)
    assert len(series) == n
    early = series[40]["dip_uptrend"]
    late = series[150]["dip_uptrend"]
    assert late >= early
    tip = detect_regime(df)
    assert tip.display_only is True
    assert "current reading" in tip.narrative.lower() or tip.display_only
