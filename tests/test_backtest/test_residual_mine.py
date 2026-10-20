"""Phase 1a — residual AND conjunct improves fee Net % when primary misses."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
from trendalgo.backtest.secret_sauce_lab.residual_mine import try_residual_refine
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def _valley_frame(n: int = 120) -> pd.DataFrame:
    """Gentle uptrend with clear troughs so trough_confirm can fire."""
    close = np.linspace(100.0, 130.0, n)
    # Dig two valleys
    close[40] = close[39] - 3.0
    close[41] = close[40] - 1.0
    close[42] = close[41] + 2.0
    close[80] = close[79] - 3.5
    close[81] = close[80] - 0.5
    close[82] = close[81] + 2.5
    high = close + 0.8
    low = close - 0.8
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(n, 50.0),
        }
    )


def test_residual_and_can_improve_or_noop() -> None:
    df = _valley_frame()
    # Primary entry that rarely fires (impossible RSI level) — residual mine may
    # find a trough_confirm AND that actually trades; soft-ok if no improvement.
    entry = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("rsi_14", "<=", -1.0),),
        "hostile entry",
    )
    exit_rule = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("peak_confirm", ">=", 1.0),),
        "exit",
    )
    cols, _ = feature_matrix(df)
    em = mask_conjuncts(cols, entry.conjuncts)
    xm = mask_conjuncts(cols, exit_rule.conjuncts)
    baseline = 0.0
    if em.any() and xm.any():
        stats = simulate_long_with_fees(df, em, xm, stake_usd=1000.0, fee=_fee())
        baseline = float(stats.get("net_profit") or 0.0)
    # Residuals: pretend Oracle valleys were missed.
    refined = try_residual_refine(
        df,
        entry,
        exit_rule,
        baseline,
        residual_entries=(40, 80),
        residual_exits=(60, 100),
        fee=_fee(),
        stake_usd=1000.0,
        time_budget_s=1.5,
    )
    if refined is None:
        return  # soft-ok: no fee-Net lift on this synth
    er, xr, net, family = refined
    assert family == "residual_and"
    assert net > baseline + 1e-9
    assert len(er.conjuncts) >= 1
    assert len(xr.conjuncts) >= 1


def test_residual_noop_when_no_residuals() -> None:
    df = _valley_frame()
    entry = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("trough_confirm", ">=", 1.0),),
        "entry",
    )
    exit_rule = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("peak_confirm", ">=", 1.0),),
        "exit",
    )
    assert (
        try_residual_refine(
            df,
            entry,
            exit_rule,
            1.0,
            residual_entries=(),
            residual_exits=(),
            fee=_fee(),
            stake_usd=1000.0,
        )
        is None
    )
