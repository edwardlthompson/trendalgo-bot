"""Secret Sauce Lab — regime-aware fee-aware causal mine."""

from __future__ import annotations

from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot, detect_regime
from trendalgo.backtest.secret_sauce_lab.run import eval_lab_trial, run_secret_sauce_lab

__all__ = [
    "RegimeSnapshot",
    "detect_regime",
    "eval_lab_trial",
    "run_secret_sauce_lab",
]
