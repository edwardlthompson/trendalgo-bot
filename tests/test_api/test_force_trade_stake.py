"""RISK-08: force-trade sizing shares compute_stake."""

from __future__ import annotations

import pytest

from trendalgo.api.routes.bots import force_stake_usd
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import StakeRejected


def test_force_stake_uses_compute_stake_caps() -> None:
    limits = RiskLimits(max_stake_usd=100, max_stake_pct=0.02)
    assert force_stake_usd(1000.0, 500.0, limits=limits) == 20.0
    assert force_stake_usd(1000.0, None, limits=limits) == 20.0
    assert force_stake_usd(1000.0, 15.0, limits=limits) == 15.0


def test_force_stake_rejects_rounded_zero() -> None:
    limits = RiskLimits(max_stake_usd=100, max_stake_pct=0.02)
    with pytest.raises(StakeRejected):
        force_stake_usd(1000.0, 0.004, limits=limits)
