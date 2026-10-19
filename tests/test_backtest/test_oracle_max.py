"""Oracle max-gain + pattern miner unit tests."""

from __future__ import annotations

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import mine_oracle_rule
from trendalgo.backtest.ta_fleet import oracle_max_row
from trendalgo.backtest.ta_simulator import simulate_oracle_max_gain
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee(*, taker: float = 0.0) -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=taker,
        maker_pct=taker,
        tier="retail",
        source_url="",
    )


def _valley_peak_frame() -> pd.DataFrame:
    # Local trough at i=2 (low=90), peak at i=4 (high=120), trough i=6, peak i=8.
    rows = [
        (100, 101, 99, 100),
        (100, 102, 98, 99),
        (99, 100, 90, 91),  # trough
        (91, 110, 90, 108),
        (108, 120, 107, 119),  # peak
        (119, 119, 100, 101),
        (101, 102, 85, 86),  # trough
        (86, 100, 85, 99),
        (99, 130, 98, 128),  # peak
        (128, 129, 120, 121),
    ]
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 1.0} for o, h, low, c in rows]
    )


def test_oracle_max_gain_known_swings() -> None:
    df = _valley_peak_frame()
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    assert stats["strategy_id"] == "ORACLE_MAX"
    assert stats["trades"] == 2
    # (120/90 - 1) + (130/85 - 1) on $1000
    expected = 1000.0 * ((120 / 90 - 1.0) + (130 / 85 - 1.0))
    assert abs(float(stats["gross_profit"]) - expected) < 1e-3
    assert float(stats["fees_paid"]) == 0.0
    assert len(stats["oracle_swings"]) == 2


def test_oracle_fees_reduce_net() -> None:
    df = _valley_peak_frame()
    free = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee(taker=0.0))
    paid = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee(taker=0.01))
    assert free is not None and paid is not None
    assert float(paid["net_profit"]) < float(free["net_profit"])
    assert float(paid["fees_paid"]) > 0


def test_oracle_short_series_safe() -> None:
    df = pd.DataFrame(
        {"open": [1, 2], "high": [1, 2], "low": [1, 2], "close": [1, 2], "volume": [1, 1]}
    )
    assert simulate_oracle_max_gain(df, stake_usd=100.0, fee=_fee()) is None
    assert oracle_max_row(df, lookback_seconds=0, stake_usd=100.0, fee=_fee()) is None


def test_mine_oracle_rule_emits_composite() -> None:
    df = _valley_peak_frame()
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    rule = mine_oracle_rule(df, oracle_trades=list(stats["oracle_swings"]), strategy_trades=[])
    assert rule is not None
    assert rule.strategy_id.startswith("GEN_ORACLE")
    assert rule.requires_backtest is True
    assert rule.conjuncts
    assert "enter when" in rule.summary()
