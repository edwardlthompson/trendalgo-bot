"""SS coverage floor, peer publish gate, soft holdout, TF remap, tradable proxy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_lab.multi_tf_lab import remap_oracle_trades
from trendalgo.backtest.secret_sauce_lab.search import (
    lab_time_budget_s,
    min_trades_for_oracle,
    search_best_pair,
)
from trendalgo.backtest.secret_sauce_lab.search_folds import (
    passes_holdout_gate,
    passes_holdout_gate_soft,
)
from trendalgo.backtest.ta_simulator import (
    simulate_oracle_max_gain,
    simulate_oracle_tradable_proxy,
)
from trendalgo.device.pair_strategy_secret_sauce import lab_oracle_row, unavailable_lab_row
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def test_min_trades_scales_with_dense_oracle() -> None:
    assert min_trades_for_oracle(0) == 1
    assert min_trades_for_oracle(2) == 1
    assert min_trades_for_oracle(10) == 3
    assert min_trades_for_oracle(27) == 5  # ceil(0.15*27)=5
    assert min_trades_for_oracle(75) == 8  # capped


def test_fee_drag_does_not_reject_losing_gross() -> None:
    from trendalgo.backtest.secret_sauce_lab.search_metrics import enrich_trial_stats

    stats = {
        "trades": 5,
        "gross_profit": -20.0,
        "fees_paid": 10.0,
        "net_profit": -30.0,
    }
    out = enrich_trial_stats(stats, stake_usd=1000.0, bh_net=-50.0, n_bars=100)
    assert out.get("reject_reason") is None
    assert out["excess_vs_bh"] == 20.0


def test_lab_budget_uncapped() -> None:
    import math

    assert math.isinf(lab_time_budget_s(5))
    assert math.isinf(lab_time_budget_s(27))
    assert math.isinf(lab_time_budget_s(500))


def test_soft_holdout_ladder() -> None:
    assert passes_holdout_gate(100.0, 70.0)
    assert not passes_holdout_gate(100.0, 55.0)
    assert passes_holdout_gate_soft(100.0, 55.0)
    assert not passes_holdout_gate_soft(100.0, 40.0)


def test_search_rejects_1_trade_when_oracle_dense(monkeypatch: pytest.MonkeyPatch) -> None:
    """Coverage floor rejects 1-trade luck when Oracle had dozens of swings."""
    n = 40
    close = np.linspace(100.0, 110.0, n)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": np.full(n, 100.0),
        }
    )
    er = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="rsi_xup_30", op=">=", value=1.0),),
        rationale="t",
    )
    xr = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="rsi_xdn_70", op=">=", value=1.0),),
        rationale="t",
    )

    def _sparse_mask(_cols: object, conjuncts: object) -> np.ndarray:
        feats = [getattr(c, "feature", "") for c in (conjuncts or ())]
        m = np.zeros(n, dtype=bool)
        if any("xup" in f for f in feats):
            m[5::12] = True
        else:
            m[10::12] = True
        return m

    def _one_trade(*_a: object, **_k: object) -> dict[str, float | int]:
        return {
            "trades": 1,
            "wins": 1,
            "net_profit": 50.0,
            "gross_profit": 50.0,
            "fees_paid": 0.0,
            "open_trades": 0,
            "tsl_hits": 0,
        }

    monkeypatch.setattr("trendalgo.backtest.secret_sauce_lab.search.mask_conjuncts", _sparse_mask)
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.search.simulate_long_with_fees", _one_trade
    )
    hit = search_best_pair(
        df,
        [(er, xr, "osc_cross")],
        fee=_fee(),
        stake_usd=1000.0,
        bh_net=0.0,
        time_budget_s=0.5,
        oracle_swing_count=27,
        require_peer_clear=False,
    )
    assert hit is None
    assert min_trades_for_oracle(27) == 5


def test_require_peer_clear_returns_none_when_under_peer() -> None:
    n = 120
    rng = np.random.default_rng(0)
    close = 100.0 + np.cumsum(rng.normal(0.05, 0.8, size=n))
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": rng.uniform(50, 200, size=n),
        }
    )
    er = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="rsi_xup_30", op="==", value=1.0),),
        rationale="t",
    )
    xr = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="rsi_xdn_70", op="==", value=1.0),),
        rationale="t",
    )
    hit = search_best_pair(
        df,
        [(er, xr, "osc_cross")],
        fee=_fee(),
        stake_usd=1000.0,
        bh_net=0.0,
        time_budget_s=1.0,
        peer_net=1_000_000.0,  # impossible peer bar
        oracle_swing_count=2,
        require_peer_clear=True,
    )
    assert hit is None


def test_remap_oracle_trades_by_timestamp() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    idx_1h = pd.DatetimeIndex([start + timedelta(hours=i) for i in range(24)], tz="UTC")
    idx_8h = pd.DatetimeIndex([start + timedelta(hours=8 * i) for i in range(4)], tz="UTC")
    frame_8h = pd.DataFrame(
        {
            "open": [1, 2, 3, 4],
            "high": [1, 2, 3, 4],
            "low": [1, 2, 3, 4],
            "close": [1, 2, 3, 4],
            "volume": [1, 1, 1, 1],
        },
        index=idx_8h,
    )
    swings = [
        {
            "entry_index": 0,
            "exit_index": 8,
            "entry_time": idx_1h[0].isoformat(),
            "exit_time": idx_1h[8].isoformat(),
        },
        {
            "entry_index": 8,
            "exit_index": 16,
            "entry_time": idx_1h[8].isoformat(),
            "exit_time": idx_1h[16].isoformat(),
        },
    ]
    remapped = remap_oracle_trades(frame_8h, swings, oracle_tf="1h", search_tf="8h")
    assert len(remapped) >= 2
    assert remapped[0]["entry_index"] == 0
    assert remapped[0]["exit_index"] == 1


def test_lab_oracle_prefers_best_not_forced_1h() -> None:
    rows = [
        {"indicator": "Oracle max", "timeframe": "1h", "net_pct": 10.0},
        {"indicator": "Oracle max", "timeframe": "8h", "net_pct": 61.8},
    ]
    picked = lab_oracle_row(rows)
    assert picked is not None
    assert picked["timeframe"] == "8h"


def test_unavailable_lab_row_has_no_fake_net() -> None:
    row = unavailable_lab_row(symbol="ETH", timeframe="8h", stake=1000.0)
    assert row.get("ss_unavailable") is True
    assert row.get("net_pct") is None
    assert "beat peers" in str(row.get("spectrum_note") or "")


def test_unavailable_upsert_clears_pending_cooking() -> None:
    from trendalgo.device.pair_strategy_secret_sauce import pending_sauce_row, upsert_secret_sauce

    pending = pending_sauce_row(symbol="ETH", timeframe="8h", stake=1000.0)
    assert pending.get("ss_lab_pending") is True
    stub = unavailable_lab_row(symbol="ETH", timeframe="8h", stake=1000.0)
    merged = upsert_secret_sauce([pending], stub)
    labs = [r for r in merged if r.get("indicator") == "Secret Sauce Lab"]
    assert len(labs) == 1
    assert labs[0].get("ss_lab_pending") is False
    assert labs[0].get("ss_unavailable") is True
    assert labs[0].get("net_pct") is None


def test_tradable_oracle_proxy_below_hl_ceiling() -> None:
    chunk = [
        (100, 101, 99, 100, 10.0),
        (100, 102, 98, 99, 12.0),
        (99, 100, 90, 91, 80.0),
        (91, 110, 90, 108, 40.0),
        (108, 120, 107, 119, 90.0),
        (119, 119, 100, 101, 15.0),
    ]
    rows: list[tuple[float, float, float, float, float]] = []
    for _ in range(8):
        rows.extend(chunk)
    df = pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": v} for o, h, low, c, v in rows]
    )
    fee = _fee()
    hl = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=fee)
    assert hl is not None
    proxy = simulate_oracle_tradable_proxy(df, list(hl["oracle_swings"]), stake_usd=1000.0, fee=fee)
    assert proxy is not None
    assert float(proxy["net_profit"]) <= float(hl["net_profit"]) + 1e-6
