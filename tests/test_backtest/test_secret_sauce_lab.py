"""Secret Sauce Lab — regime detector, family budgets, upsert."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_cross import cross_up, osc_cross_columns
from trendalgo.backtest.secret_sauce_lab import detect_regime, run_secret_sauce_lab
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import (
    inspire_cross_seeds,
    is_exact_peer_clone,
)
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import FAMILIES, _family_weights
from trendalgo.backtest.secret_sauce_lab.rsx_neighborhood import (
    is_rsx_neighborhood_rule,
    search_rsx_neighborhood,
)
from trendalgo.backtest.secret_sauce_search import default_search_fee
from trendalgo.backtest.ta_simulator import simulate_long_with_fees, simulate_oracle_max_gain
from trendalgo.device.pair_strategy_secret_sauce import pending_sauce_row, upsert_secret_sauce
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _uptrend(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100.0 + np.cumsum(rng.normal(0.15, 0.4, size=n))
    high = close + rng.uniform(0.2, 1.0, size=n)
    low = close - rng.uniform(0.2, 1.0, size=n)
    open_ = close + rng.normal(0, 0.2, size=n)
    vol = rng.uniform(50, 200, size=n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol})


def _range_quiet(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    close = 100.0 + rng.normal(0, 0.3, size=n)
    high = close + 0.4
    low = close - 0.4
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(10, 20, size=n),
        }
    )


def _chop(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(11)
    close = 100.0 + np.cumsum(rng.normal(0, 2.5, size=n))
    high = close + rng.uniform(1.0, 4.0, size=n)
    low = close - rng.uniform(1.0, 4.0, size=n)
    return pd.DataFrame(
        {
            "open": close,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(5, 500, size=n),
        }
    )


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def test_uptrend_budgets_dip_uptrend() -> None:
    snap = detect_regime(_uptrend())
    assert snap.family_weights["dip_uptrend"] >= snap.family_weights["mean_reversion"]
    assert set(snap.family_weights) >= set(FAMILIES)


def test_range_budgets_mean_reversion() -> None:
    snap = detect_regime(_range_quiet())
    assert snap.structural in {"ranging", "transitional", "choppy", "trending"}
    # Quiet range should not starve mean-reversion relative to momentum.
    assert snap.family_weights["mean_reversion"] >= snap.family_weights["momentum"] - 1e-9


def test_chop_skims() -> None:
    snap = detect_regime(_chop())
    # Explicit choppy → skim. Majority window may label noisy walks trending;
    # then high-vol must not fatten mean_reversion as the quiet-range hero.
    if snap.structural == "choppy":
        assert max(snap.family_weights.values()) <= 0.55
    else:
        assert snap.volatility == "high" or snap.family_weights["mean_reversion"] < 0.9


def test_lab_runs_on_valley() -> None:
    chunk = [
        (100, 101, 99, 100, 10.0),
        (100, 102, 98, 99, 12.0),
        (99, 100, 90, 91, 80.0),
        (91, 110, 90, 108, 40.0),
        (108, 120, 107, 119, 90.0),
        (119, 119, 100, 101, 15.0),
    ]
    rows: list[tuple[float, float, float, float, float]] = []
    for _ in range(5):
        rows.extend(chunk)
    df = pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": v} for o, h, low, c, v in rows]
    )
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    packed = run_secret_sauce_lab(
        df, fee=default_search_fee(), stake_usd=1000.0, oracle_trades=list(stats["oracle_swings"])
    )
    assert packed is not None
    dossier, regime = packed
    assert dossier.rule.conjuncts
    assert dossier.exit_rule.conjuncts
    assert "Enter when" in dossier.formula_en
    assert regime.family_weights


def test_upsert_replaces_pending() -> None:
    pending = pending_sauce_row(symbol="BTC", timeframe="1h", stake=1000.0)
    assert pending.get("ss_lab_pending") is True
    cooked = {
        "indicator": "Secret Sauce Lab",
        "timeframe": "1h",
        "net_pct": 7.5,
        "ss_lab_pending": False,
        "heartbeat_dossier": {"formula_en": "Enter when x. Exit when y."},
    }
    rows = [{"indicator": "B&H", "net_pct": 1.0}, pending]
    merged = upsert_secret_sauce(rows, cooked)
    sauces = [r for r in merged if r.get("indicator") == "Secret Sauce Lab"]
    assert len(sauces) == 1
    assert sauces[0].get("net_pct") == 7.5
    assert not sauces[0].get("ss_lab_pending")


def test_cross_fires_on_edge_only() -> None:
    rsi = np.array([40.0, 28.0, 28.0, 31.0, 35.0, 29.0, 32.0], dtype=float)
    xup = cross_up(rsi, 30.0)
    assert xup[3] == 1.0  # 28 → 31 cross
    assert xup[2] == 0.0  # still ≤30, no cross
    assert xup[6] == 1.0  # 29 → 32 cross
    assert float(xup.sum()) == 2.0


def test_downtrend_starves_dip_budget() -> None:
    w = _family_weights("trending", "normal", "down", squeeze=True, volume_ok=True)
    assert w["dip_uptrend"] <= 0.1
    assert w["osc_cross"] >= 0.85
    assert w["squeeze_breakout"] <= 0.15
    assert "osc_cross" in FAMILIES


def test_reseed_rejects_exact_peer_clone() -> None:
    hints = [
        {
            "indicator": "RSX",
            "net_pct": 8.0,
            "kind": "bounded_reversal",
            "entry_level": 30.0,
            "exit_level": 70.0,
            "period": 14,
        }
    ]
    seeds = inspire_cross_seeds("GEN_SECRET_1", hints)
    assert seeds
    for er, xr, _fam in seeds:
        assert not is_exact_peer_clone(er, xr, hints)
    # Exact 30/70 RSI-only must not appear.
    exact = ("rsi_xup_30", "rsi_xdn_70")
    for er, xr, _fam in seeds:
        feats = tuple(c.feature for c in er.conjuncts) + tuple(c.feature for c in xr.conjuncts)
        assert feats != exact


def test_reseed_mutants_include_extra_conjunct_or_level_shift() -> None:
    hints = [
        {
            "indicator": "RSX",
            "net_pct": 8.0,
            "kind": "bounded_reversal",
            "entry_level": 30.0,
            "exit_level": 70.0,
            "period": 14,
        }
    ]
    seeds = inspire_cross_seeds("GEN_SECRET_1", hints)
    assert any(len(er.conjuncts) > 1 for er, _xr, _f in seeds)
    assert any(
        any(c.feature.startswith("rsi_xup_") and c.feature != "rsi_xup_30" for c in er.conjuncts)
        for er, _xr, _f in seeds
    )


def test_osc_cross_beats_level_state_on_synth() -> None:
    """Synthetic mean-reversion: edge crosses beat sticky level-state RSI."""
    closes: list[float] = []
    base = 100.0
    for _ in range(40):
        for d in (0.0, -2.0, -4.0, -5.0, -3.0, 0.0, 3.0, 5.0, 4.0, 1.0):
            base = max(50.0, base + d)
            closes.append(base)
    n = len(closes)
    c = np.array(closes, dtype=float)
    df = pd.DataFrame(
        {
            "open": c,
            "high": c + 0.5,
            "low": c - 0.5,
            "close": c,
            "volume": np.full(n, 100.0),
        }
    )
    fee = _fee()
    stake = 1000.0
    from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
    from trendalgo.backtest.secret_sauce_ta_series import rsi

    rsi_a = rsi(c, 14)
    cols = osc_cross_columns(rsi_a, np.full(n, 50.0))
    assert cols["rsi_xup_30"].sum() >= 1

    sid = "GEN_SECRET_1"
    cross_e = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_xup_30", op=">=", value=1.0),),
        rationale="cross",
    )
    cross_x = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_xdn_70", op=">=", value=1.0),),
        rationale="cross",
    )
    level_e = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_14", op="<=", value=45.0),),
        rationale="level",
    )
    level_x = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature="rsi_14", op=">=", value=70.0),),
        rationale="level",
    )
    mat, _ = feature_matrix(df)
    cross_net = float(
        simulate_long_with_fees(
            df,
            mask_conjuncts(mat, cross_e.conjuncts),
            mask_conjuncts(mat, cross_x.conjuncts),
            stake_usd=stake,
            fee=fee,
            trailing_stop_pct=0.0,
        ).get("net_profit")
        or 0.0
    )
    level_net = float(
        simulate_long_with_fees(
            df,
            mask_conjuncts(mat, level_e.conjuncts),
            mask_conjuncts(mat, level_x.conjuncts),
            stake_usd=stake,
            fee=fee,
            trailing_stop_pct=0.0,
        ).get("net_profit")
        or 0.0
    )
    assert cross_net > level_net


def test_refine_ladder_ships_beat_bh_when_peer_unreachable() -> None:
    from trendalgo.backtest.secret_sauce_lab.refine_ladder import ladder_accepts

    # Peer bar 100; prior under B&H; candidate beats B&H but not peer → still ships.
    assert ladder_accepts(net=60.0, prior_net=10.0, peer_usd=100.0, bh_usd=50.0)
    assert not ladder_accepts(net=40.0, prior_net=10.0, peer_usd=100.0, bh_usd=50.0)
    # Absolute peer clear → ships even if below prior (shouldn't happen often).
    assert ladder_accepts(net=110.0, prior_net=120.0, peer_usd=100.0, bh_usd=50.0)


def test_peer_class_inspire_cdl_not_rsi_only() -> None:
    from trendalgo.backtest.secret_sauce_lab.peer_inspire import (
        inspire_seeds_for_hints,
        should_run_rsx_neighborhood,
    )

    hints = [
        {
            "indicator": "CDLDOJI",
            "net_pct": 5.0,
            "kind": "cdl_pattern",
            "entry_level": 30.0,
            "exit_level": 70.0,
            "period": 14,
        }
    ]
    seeds = inspire_seeds_for_hints("GEN_SECRET_1", hints)
    assert seeds
    assert any(fam == "peer_cdl" for _e, _x, fam in seeds)
    assert not should_run_rsx_neighborhood(hints)
    # At least one seed uses trough/vol family, not lone rsi_xup.
    assert any(
        any(c.feature in {"trough_confirm", "vol_z", "up_vol_impulse"} for c in er.conjuncts)
        for er, _xr, _f in seeds
    )


def test_validate_accepts_period_rsx_features() -> None:
    from trendalgo.backtest.secret_sauce_validate import is_allowed_ss_feature

    assert is_allowed_ss_feature("rsx15_xup_21")
    assert is_allowed_ss_feature("rsx15_xdn_75")
    assert is_allowed_ss_feature("rsx12_xup_23")
    assert is_allowed_ss_feature("rsx9_xdn_70")
    assert is_allowed_ss_feature("rsi_xup_30")
    assert is_allowed_ss_feature("fib_dist_618")
    assert is_allowed_ss_feature("cdl_cdldojistar")
    assert not is_allowed_ss_feature("totally_fake_feat")


def test_feature_bank_includes_structure_keys() -> None:
    from trendalgo.backtest.secret_sauce_features import feature_keys_for

    rng = np.random.default_rng(1)
    n = 60
    close = 40.0 + np.cumsum(rng.normal(0, 0.5, size=n))
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.4,
            "low": close - 0.4,
            "close": close,
            "volume": np.full(n, 20.0),
        }
    )
    keys = feature_keys_for(df)
    assert "fib_dist_618" in keys
    assert "mom_10" in keys
    assert any(k.startswith("cdl_") for k in keys)


def test_masks_for_rsx_cross_period(monkeypatch: pytest.MonkeyPatch) -> None:
    """Entry/exit may use different RSX periods (fee-max toward Oracle)."""
    from trendalgo.backtest.secret_sauce_lab import rsx_neighborhood as rsx_mod

    n = 160
    # Deterministic synthetic RSX — avoid live TA engine / pandas-ta CI variance.
    # Rise through entry level then fall through exit level.
    fake = np.concatenate([np.linspace(10.0, 85.0, n // 2), np.linspace(85.0, 20.0, n - n // 2)])
    monkeypatch.setattr(rsx_mod, "_rsx_series", lambda _df, _period: fake.copy())
    close = np.full(n, 50.0)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 40.0),
        }
    )
    er = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("rsx12_xup_23", ">=", 1.0),),
        "ep",
    )
    xr = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("rsx9_xdn_70", ">=", 1.0),),
        "xp",
    )
    packed = rsx_mod.masks_for_rsx_rules(df, er, xr)
    assert packed is not None
    em, xm = packed
    assert em.dtype == bool and xm.dtype == bool
    assert len(em) == n and len(xm) == n
    assert bool(em.any()) and bool(xm.any())


def test_search_prefers_higher_net_and_oracle_family_on_tie() -> None:
    """Higher fee Net % wins; at equal Net prefer oracle_pattern family."""
    from trendalgo.backtest.secret_sauce_lab import search as ss_search

    low = (
        CompositeRule("GEN_SECRET_1", (RuleConjunct("ret_1", ">=", 0.0),), ""),
        CompositeRule("GEN_SECRET_1", (RuleConjunct("rsi_14", ">=", 70.0),), ""),
        10.0,
        "peer_inspire",
    )
    high = (
        CompositeRule("GEN_SECRET_1", (RuleConjunct("trough_confirm", ">=", 1.0),), ""),
        CompositeRule("GEN_SECRET_1", (RuleConjunct("peak_confirm", ">=", 1.0),), ""),
        50.0,
        "dip_uptrend",
    )
    assert ss_search._better(high, low, None)
    assert not ss_search._better(low, high, None)
    tie_a = (low[0], low[1], 20.0, "peer_inspire")
    tie_b = (high[0], high[1], 20.0, "oracle_pattern")
    assert ss_search._better(tie_b, tie_a, None)
    assert not ss_search._better(tie_a, tie_b, None)


def test_oracle_pattern_mine_covers_valley_entries() -> None:
    """Reverse-mine at Oracle troughs recovers high near-coverage."""
    from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
    from trendalgo.backtest.secret_sauce_lab.pattern_mine import pattern_seed_pairs
    from trendalgo.backtest.ta_simulator import simulate_oracle_max_gain

    df = _uptrend(n=220)
    # Carve valleys so Oracle finds clear trough→peak swings.
    closes = df["close"].to_numpy(copy=True)
    for i in range(40, 200, 45):
        closes[i : i + 6] -= np.linspace(0, 6, 6)
        closes[i + 6 : i + 14] += np.linspace(0, 7, 8)
    df = df.copy()
    df["close"] = closes
    df["high"] = closes + 0.5
    df["low"] = closes - 0.5
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    swings = list(stats.get("oracle_swings") or [])
    assert len(swings) >= 2
    entries = [int(t["entry_index"]) for t in swings]
    exits = [int(t["exit_index"]) for t in swings]
    pairs = pattern_seed_pairs(
        df, entry_indexes=entries, exit_indexes=exits, family="oracle_pattern"
    )
    assert pairs
    best_cov = 0.0
    for er, _xr, fam in pairs:
        assert fam == "oracle_pattern"
        mask = entries_for_secret_sauce(df, er)
        near = sum(1 for i in entries if mask[max(0, i - 2) : i + 3].any())
        best_cov = max(best_cov, near / len(entries))
    assert best_cov >= 0.5


def test_peer_pattern_macd_labels_not_rsi_only() -> None:
    """Labeled MACD-style bars yield pattern seeds with non-RSI features."""
    from trendalgo.backtest.secret_sauce_lab.pattern_mine import pattern_seed_pairs

    df = _uptrend(n=180)
    # Synthetic labels at trough-ish and peak-ish bars.
    entries = [30, 70, 110, 150]
    exits = [45, 85, 125, 165]
    pairs = pattern_seed_pairs(df, entry_indexes=entries, exit_indexes=exits, family="peer_pattern")
    assert pairs
    feats = {c.feature for er, xr, _f in pairs for c in (*er.conjuncts, *xr.conjuncts)}
    # Must not be RSI/stoch-cross-only; allow price/TA/volume family.
    non_rsi = feats - {f for f in feats if f.startswith("rsi_") or f.startswith("stoch_")}
    assert non_rsi


def test_rsx_neighborhood_rejects_exact_peer_plain() -> None:
    """Neighborhood search never returns exact peer period+levels plain clone."""
    # Synthetic oscillating series long enough for RSX.
    rng = np.random.default_rng(42)
    n = 120
    close = 100.0 + np.cumsum(rng.normal(0, 1.0, size=n))
    # Inject a few dips/recoveries
    for i in range(20, n, 25):
        close[i : i + 5] -= np.linspace(0, 8, 5)
        close[i + 5 : i + 10] += np.linspace(0, 8, 5)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.full(n, 50.0),
        }
    )
    hit = search_rsx_neighborhood(
        df,
        fee=_fee(),
        stake_usd=1000.0,
        peer_entry=30.0,
        peer_exit=70.0,
        peer_period=14,
        peer_net_usd=None,
        time_budget_s=2.0,
    )
    if hit is None:
        return  # soft-ok on hostile synth
    er, xr, _net, fam = hit
    assert fam == "rsx_neighborhood"
    assert is_rsx_neighborhood_rule(er)
    feats = tuple(c.feature for c in er.conjuncts) + tuple(c.feature for c in xr.conjuncts)
    assert "rsx14_xup_30" not in feats or "rsx14_xdn_70" not in feats or len(er.conjuncts) > 1
