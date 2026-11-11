"""SIM-04: relaxed spectrum gate; oracle may take losing swings."""

from __future__ import annotations

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_validate import validate_secret_sauce
from trendalgo.backtest.ta_simulator import simulate_oracle_max_gain
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=0.0,
        maker_pct=0.0,
        tier="retail",
        source_url="",
    )


def _dossier() -> HeartbeatDossier:
    entry = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="trough_confirm", op=">=", value=1.0),),
        rationale="e",
    )
    exit_r = CompositeRule(
        strategy_id="GEN_SECRET_1",
        conjuncts=(RuleConjunct(feature="peak_confirm", op=">=", value=1.0),),
        rationale="x",
    )
    return HeartbeatDossier(
        rule=entry,
        exit_rule=exit_r,
        formula_en="t",
        train_coverage=1.0,
        holdout_coverage=1.0,
        swing_hits=(True,),
        exit_hits=(True,),
        oracle_entry_indexes=(1,),
        oracle_exit_indexes=(2,),
        anti_cheat="t",
        trailing_stop_pct=0.0,
    )


def test_spectrum_ok_above_oracle_within_five_pct(monkeypatch) -> None:  # noqa: ANN001
    import numpy as np

    closes = [100.0, 100.0, 100.0, 105.0, 110.0, 110.0]
    df = pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
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
    from trendalgo.backtest.ta_simulator import simulate_long_with_fees

    stats = simulate_long_with_fees(df, entries, exits, stake_usd=1000.0, fee=_fee())
    trial_net = float(stats["net_profit"]) / 1000.0 * 100.0
    # Peer below trial; oracle slightly below trial (trial beats oracle within 5%).
    ok, reason = validate_secret_sauce(
        _dossier(),
        df,
        {"net_pct": trial_net},
        fee=_fee(),
        stake_usd=1000.0,
        oracle_net=trial_net * 0.98,
        peer_net=0.0,
    )
    assert ok, reason
    assert reason == "spectrum_ok_above_oracle"


def test_oracle_choppy_fixture_win_rate_below_100() -> None:
    # L@1=10 → H@3=8 (loser), L@5=5 → H@6=20 (winner).
    highs = [12.0, 11.0, 7.0, 8.0, 7.0, 6.0, 20.0, 5.0]
    lows = [11.0, 10.0, 10.5, 7.0, 6.0, 5.0, 15.0, 4.0]
    df = pd.DataFrame(
        {
            "open": [10.0] * 8,
            "high": highs,
            "low": lows,
            "close": [10.0] * 8,
            "volume": [1.0] * 8,
        }
    )
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    assert stats["trades"] >= 2
    assert float(stats["win_rate"]) < 1.0
    assert int(stats["wins"]) < int(stats["trades"])
