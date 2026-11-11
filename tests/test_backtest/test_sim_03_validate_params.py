"""SIM-03: validate uses dossier.eval_params() including TSL."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_validate import validate_secret_sauce
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=0.0,
        maker_pct=0.0,
        tier="retail",
        source_url="",
    )


def _dossier(tsl: float) -> HeartbeatDossier:
    entry = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="trough_confirm", op=">=", value=1.0),),
        rationale="entry",
    )
    exit_r = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="peak_confirm", op=">=", value=1.0),),
        rationale="exit",
    )
    return HeartbeatDossier(
        rule=entry,
        exit_rule=exit_r,
        formula_en="test",
        train_coverage=0.5,
        holdout_coverage=0.5,
        swing_hits=(True,),
        exit_hits=(True,),
        oracle_entry_indexes=(1,),
        oracle_exit_indexes=(3,),
        anti_cheat="test",
        trailing_stop_pct=tsl,
    )


def test_eval_params_includes_trailing_stop() -> None:
    assert _dossier(0.03).eval_params()["trailing_stop_pct"] == 0.03


def test_validate_nonzero_tsl_and_net_mismatch(monkeypatch) -> None:  # noqa: ANN001
    # Entry fills next bar at 100; TSL 50% never hits; exit signal fills next bar at 110.
    closes = [100.0, 100.0, 100.0, 105.0, 110.0, 110.0]
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1.0] * len(closes),
        }
    )
    entries = np.array([False, True, False, False, False, False])
    exits = np.array([False, False, False, False, True, False])

    def _masks(_df, entry_conjuncts, exit_conjuncts):  # noqa: ANN001
        del _df, entry_conjuncts, exit_conjuncts
        return entries, exits

    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_validate.masks_for_secret_sauce",
        _masks,
    )
    dossier = _dossier(0.50)
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=_fee(),
        trailing_stop_pct=0.50,
    )
    trial_net = float(stats["net_profit"]) / 1000.0 * 100.0
    assert trial_net > 0
    ok, reason = validate_secret_sauce(
        dossier,
        df,
        {"net_pct": trial_net},
        fee=_fee(),
        stake_usd=1000.0,
        oracle_net=trial_net + 1.0,
        peer_net=0.0,
    )
    assert ok, reason
    bad, reason2 = validate_secret_sauce(
        dossier,
        df,
        {"net_pct": trial_net + 5.0},
        fee=_fee(),
        stake_usd=1000.0,
        oracle_net=trial_net + 10.0,
        peer_net=-50.0,
    )
    assert not bad
    assert reason2.startswith("net_mismatch")
    assert "tsl=" in reason2
