"""RISK-05: compute_stake raises StakeRejected when the rounded stake is <= 0."""

from __future__ import annotations

import pytest

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager, StakeRejected


def test_tiny_stake_raises_after_round() -> None:
    mgr = RiskManager(RiskLimits(max_stake_usd=100, max_stake_pct=0.02), wallet_usd=1000.0)
    with pytest.raises(StakeRejected, match="minimum"):
        mgr.compute_stake(0.004)
