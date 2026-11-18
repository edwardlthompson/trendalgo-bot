"""SIM-08: permutation null percentile + stability badges."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix
from trendalgo.backtest.secret_sauce_lab.search import SearchHit
from trendalgo.backtest.secret_sauce_lab.search_null import annotate_stability
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def test_noise_series_sub_95th_badge() -> None:
    rng = np.random.default_rng(0)
    n = 120
    close = 100.0 + np.cumsum(rng.normal(0, 1.0, size=n))
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.ones(n) * 10,
        }
    )
    cols, _ = feature_matrix(df)
    hit = SearchHit(
        CompositeRule("GEN_SECRET_1", (RuleConjunct("above_sma20", ">=", 1.0),), ""),
        CompositeRule("GEN_SECRET_1", (RuleConjunct("peak_confirm", ">=", 1.0),), ""),
        net=1.0,
        family="noise",
        trailing_stop_pct=0.0,
    )
    out = annotate_stability(hit, df=df, cols=cols, fee=_fee(), stake_usd=1000.0, trial_count=10)
    assert out.null_percentile is not None
    assert out.stability in {
        "not_distinguishable_from_chance",
        "fragile",
        "stable",
    }
    # Noise recipes should usually not clear the 95th null bar.
    assert out.null_percentile < 0.95 or out.stability == "not_distinguishable_from_chance"
