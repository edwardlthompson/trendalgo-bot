"""Extra coverage for sauce_cook helpers / Final path (no full All-TA scan)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_lab.dual_horizon import cook_dual_horizon
from trendalgo.backtest.secret_sauce_lab.genetic_search import cook_genetic
from trendalgo.backtest.secret_sauce_lab.helper_armed import arming_mask
from trendalgo.backtest.secret_sauce_lab.meta_tsl import _TSL_GRID, best_tsl_for_row
from trendalgo.backtest.secret_sauce_lab.regime_peers import regime_matched_peer_hints
from trendalgo.backtest.secret_sauce_lab.sauce_cook import cook_sauce_suite
from trendalgo.backtest.secret_sauce_lab.teacher_distill import cook_teacher_distill
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=0.001,
        maker_pct=0.001,
        tier="retail",
        source_url="",
    )


def _frame(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    idx = pd.date_range("2024-06-01", periods=n, freq="h", tz="UTC")
    close = 50 + np.cumsum(rng.normal(0.02, 0.5, size=n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": rng.uniform(50, 200, size=n),
        },
        index=idx,
    )


def test_arming_mask_bool() -> None:
    m = arming_mask(_frame())
    assert m.dtype == bool
    assert len(m) == 100


def test_regime_peers_fallback() -> None:
    rows = [{"indicator": "RSI", "net_pct": 1.0, "params": {"period": 14}}]
    hints = regime_matched_peer_hints(rows, structural="trending")
    assert isinstance(hints, list)


def test_genetic_and_teacher_soft() -> None:
    df = _frame(80)
    fee = _fee()
    # May return None on weak tape — must not raise.
    cook_genetic(df, fee=fee, stake_usd=100.0, oracle_swing_count=3)
    cook_teacher_distill(df, [], fee=fee, stake_usd=100.0)


def test_meta_tsl_grid() -> None:
    assert max(_TSL_GRID) == 0.20
    tsl, net = best_tsl_for_row(_frame(), {"net_profit": 1.0}, fee=_fee(), stake_usd=100.0)
    assert tsl >= 0.0
    assert isinstance(net, float)


def test_cook_sauce_suite_empty_oracle() -> None:
    df = _frame()
    out = cook_sauce_suite(
        oracle={"timeframe": "1h", "oracle_swings": []},
        rows=[],
        frames_by_tf={"1h": df},
        symbol="ETH",
        stake=100.0,
        fee=_fee(),
        core_lab=None,
        sauce_ta=None,
    )
    assert isinstance(out, list)


def test_cook_sauce_suite_with_peers() -> None:
    df = _frame(160)
    peers = [
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "net_pct": 8.0,
            "params": {"period": 14, "buy_level": 30, "sell_level": 70},
            "regime": {"structural": "trending"},
        },
        {
            "indicator": "Stochastic",
            "timeframe": "1h",
            "net_pct": 6.0,
            "params": {"period": 14, "buy_level": 20, "sell_level": 80},
        },
    ]
    out = cook_sauce_suite(
        oracle={"timeframe": "1h", "oracle_swings": [{"entry_index": 20, "exit_index": 40}]},
        rows=peers,
        frames_by_tf={"1h": df, "4h": df.iloc[::4].copy()},
        symbol="ETH",
        stake=1000.0,
        fee=_fee(),
        core_lab=None,
        sauce_ta=None,
    )
    assert isinstance(out, list)
    # Soft: may be empty on weak random tape; must never raise.


def test_dual_horizon_none_without_frames() -> None:
    assert (
        cook_dual_horizon(
            {},
            oracle_tf="1h",
            oracle_trades=[],
            fee=_fee(),
            stake=100.0,
            symbol="ETH",
        )
        is None
    )
