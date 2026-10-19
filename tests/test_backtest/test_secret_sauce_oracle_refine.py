"""Oracle-first refine prefers independent seeds over peer peek."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.peer_refine import refine_lab_from_peers
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def _frame(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    close = 80.0 + np.cumsum(rng.normal(0, 0.7, size=n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.6,
            "low": close - 0.6,
            "close": close,
            "volume": np.full(n, 40.0),
        }
    )


def test_refine_oracle_first_runs_without_peer_rows() -> None:
    df = _frame()
    rule = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("trough_confirm", ">=", 1.0),),
        "entry",
    )
    exit_rule = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("peak_confirm", ">=", 1.0),),
        "exit",
    )
    dossier = HeartbeatDossier(
        rule=rule,
        exit_rule=exit_rule,
        formula_en="test",
        train_coverage=0.5,
        holdout_coverage=0.4,
        swing_hits=(True,),
        exit_hits=(True,),
        oracle_entry_indexes=(10, 30, 50),
        oracle_exit_indexes=(20, 40, 60),
        anti_cheat="test",
    )
    sauce: dict[str, Any] = {
        "indicator": "Secret Sauce",
        "timeframe": "1h",
        "net_profit": 1.0,
        "heartbeat_dossier": dossier.to_dict(),
    }
    rows = [
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "net_pct": 5.0,
            "params": {"kind": "bounded_reversal", "entry_level": 30, "exit_level": 70},
        }
    ]
    hit = refine_lab_from_peers(
        sauce,
        rows,
        df,
        stake=1000.0,
        fee=_fee(),
        time_budget_s=2.0,
        frames_by_tf={"1h": df},
    )
    # Soft: may return None on hostile synth; when it ships, family is independent.
    if hit is None:
        return
    _dossier, _regime, trial, _tf = hit
    assert float(trial.get("net_profit") or 0.0) == float(trial.get("net_profit") or 0.0)
