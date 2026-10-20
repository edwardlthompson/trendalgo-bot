"""Phase 0 — residual Oracle indexes + causal feature hits on dossier."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier, dossier_from_dict
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix
from trendalgo.backtest.secret_sauce_lab.residual_instrument import (
    build_residual_fields,
    residual_indexes,
    true_features_at,
)


def _frame(n: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(21)
    close = 100.0 + np.cumsum(rng.normal(0.05, 0.5, size=n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": rng.uniform(20, 80, size=n),
        }
    )


def test_residual_indexes_lists_misses() -> None:
    assert residual_indexes([10, 20, 30], (True, False, True)) == (20,)
    assert residual_indexes([10], (True,)) == ()


def test_build_residual_fields_missed_entry_and_gap() -> None:
    df = _frame()
    residual = build_residual_fields(
        df,
        entries=[10, 40],
        exits=[20, 50],
        swing_hits=(True, False),
        exit_hits=(True, True),
        sauce_net=5.0,
        oracle_net=12.0,
    )
    assert residual["residual_entry_indexes"] == (40,)
    assert residual["residual_exit_indexes"] == ()
    assert residual["oracle_gap_net_pct"] == 7.0
    hits = residual["residual_feature_hits"]
    assert len(hits) == 1
    assert hits[0]["side"] == "entry"
    assert hits[0]["index"] == 40
    assert isinstance(hits[0]["features"], list)
    # Features reported are from the causal matrix and fire as binary ≈1.
    cols, _ = feature_matrix(df)
    for name in hits[0]["features"]:
        assert name in cols
        assert abs(float(cols[name][40]) - 1.0) < 1e-6


def test_true_features_at_caps_and_binary_only() -> None:
    cols = {
        "rsi_xup_30": np.array([0.0, 1.0, 0.0]),
        "rsi_14": np.array([40.0, 25.0, 60.0]),  # continuous — not a binary fire
        "local_trough": np.array([0.0, 1.0, 0.0]),
    }
    assert true_features_at(cols, 1, top_n=8) == ["rsi_xup_30", "local_trough"]
    assert true_features_at(cols, 0) == []


def test_dossier_roundtrip_residuals() -> None:
    rule = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("rsi_xup_30", ">=", 1.0),),
        "entry",
    )
    exit_rule = CompositeRule(
        "GEN_SECRET_1",
        (RuleConjunct("rsi_xdn_70", ">=", 1.0),),
        "exit",
    )
    dossier = HeartbeatDossier(
        rule=rule,
        exit_rule=exit_rule,
        formula_en="test",
        train_coverage=0.5,
        holdout_coverage=0.4,
        swing_hits=(True, False),
        exit_hits=(True, True),
        oracle_entry_indexes=(10, 40),
        oracle_exit_indexes=(20, 50),
        anti_cheat="test",
        residual_entry_indexes=(40,),
        residual_exit_indexes=(),
        residual_feature_hits=({"side": "entry", "index": 40, "features": ["local_trough"]},),
        oracle_gap_net_pct=3.5,
    )
    restored = dossier_from_dict(dossier.to_dict())
    assert restored is not None
    assert restored.residual_entry_indexes == (40,)
    assert restored.oracle_gap_net_pct == 3.5
    assert restored.residual_feature_hits[0]["features"] == ["local_trough"]
    # eval_params stays slim (no residual dump).
    assert "residual_entry_indexes" not in dossier.eval_params()
