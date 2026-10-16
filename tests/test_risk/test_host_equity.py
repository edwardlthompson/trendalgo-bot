"""R3: one host RiskManager sizes from host equity; zero or negative stakes place no order."""

from __future__ import annotations

import pytest

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager, StakeRejected
from trendalgo.risk.strategy_mixins import RiskGuardMixin

LIMITS = RiskLimits(max_stake_usd=1000, max_stake_pct=0.02)


def _strategy(host: RiskManager) -> RiskGuardMixin:
    strat = RiskGuardMixin()
    strat.risk_limits = LIMITS
    strat.risk_manager = host
    return strat


def test_five_thousand_dollars_of_equity_sizes_at_two_percent() -> None:
    mgr = RiskManager(LIMITS, wallet_usd=1000)
    assert mgr.set_equity(balance_usd=4500, open_position_usd=500) == 5000
    assert mgr.compute_stake(500) == 100.0  # 2% of 5,000
    assert mgr.compute_stake(50) == 50.0


def test_zero_and_negative_stakes_are_rejected() -> None:
    mgr = RiskManager(LIMITS, wallet_usd=5000)
    for stake in (0.0, -10.0, float("nan")):
        with pytest.raises(StakeRejected):
            mgr.compute_stake(stake)


def test_equity_inputs_must_be_finite() -> None:
    mgr = RiskManager(LIMITS, wallet_usd=1000)
    with pytest.raises(ValueError, match="finite"):
        mgr.set_equity(balance_usd=float("inf"))


def test_a_zero_stake_places_no_order() -> None:
    strat = _strategy(RiskManager(LIMITS, wallet_usd=5000))
    stake = strat.risk_custom_stake_amount(
        "BTC/USD", None, 50_000, 0.0, None, None, 1, None, "long"
    )
    assert stake == 0.0


def test_the_host_manager_is_the_one_used() -> None:
    host = RiskManager(LIMITS, wallet_usd=5000)
    strat = _strategy(host)
    stake = strat.risk_custom_stake_amount(
        "BTC/USD", None, 50_000, 500, None, None, 1, None, "long"
    )
    assert stake == 100.0  # 2% of the host's 5,000, not a new 1,000 manager
    assert strat._ensure_risk_manager() is host
