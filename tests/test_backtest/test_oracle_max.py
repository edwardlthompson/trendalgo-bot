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
    # Zigzag densify may add legs beyond the two major fractal swings; regenerate
    # golden counts deliberately when ORACLE_ZIGZAG_MIN_MOVE_PCT changes.
    assert stats["trades"] >= 2
    assert float(stats["win_rate"]) == 1.0
    pairs = {(float(t["entry_price"]), float(t["exit_price"])) for t in stats["oracle_swings"]}
    assert (90.0, 120.0) in pairs
    assert (85.0, 130.0) in pairs
    assert float(stats["fees_paid"]) == 0.0
    assert float(stats["gross_profit"]) > 0.0
    assert len(stats["oracle_swings"]) == int(stats["trades"])


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


def test_zigzag_densifies_beyond_fractal_only() -> None:
    """0.25% zigzag must beat collapsed fractals on a choppy 1h-like series."""
    import numpy as np

    from trendalgo.backtest.ta_simulator import (
        ORACLE_SWING_CAP,
        _alternate_collapse,
        _fractal_swings,
        _swing_points,
        _zigzag_swings,
    )

    rng = np.random.default_rng(7)
    n = 720  # ~30d of 1h bars
    base = 100.0
    closes = [base]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1.0 + float(rng.normal(0.0, 0.004))))
    highs = np.array([c * 1.002 for c in closes], dtype=float)
    lows = np.array([c * 0.998 for c in closes], dtype=float)
    fractal_n = len(_alternate_collapse(_fractal_swings(highs, lows)))
    zigzag_n = len(_alternate_collapse(_zigzag_swings(highs, lows, min_move_pct=0.25)))
    assert zigzag_n > fractal_n
    merged = _swing_points(highs, lows)
    assert len(merged) == zigzag_n
    assert len(merged) < ORACLE_SWING_CAP
    kinds = [k for _, k, _ in merged]
    assert all(kinds[i] != kinds[i + 1] for i in range(len(kinds) - 1))
    assert all(merged[i][0] != merged[i + 1][0] for i in range(len(merged) - 1))


def test_oracle_skips_fee_negative_peaks() -> None:
    # Tiny winner peak that does not clear 1% RT fees must not open a trade.
    rows = [
        (100, 101, 99, 100),
        (100, 102, 98, 99),
        (99, 100, 90, 91),  # trough
        (91, 91.2, 90, 91),
        (91.2, 91.4, 91, 91.3),  # peak ~0.44% — below 2% RT at taker=0.01
        (91.3, 91.3, 91, 91),
    ]
    df = pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": 1.0} for o, h, low, c in rows]
    )
    assert simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee(taker=0.01)) is None
