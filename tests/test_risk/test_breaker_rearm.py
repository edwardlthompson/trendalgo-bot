"""RISK-04: reset_breaker keeps peak; peak reset is a separate command."""

from __future__ import annotations

import logging

import pytest

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager


def test_reset_keeps_peak_recovery_then_retrips(caplog: pytest.LogCaptureFixture) -> None:
    limits = RiskLimits(circuit_breaker_drawdown_pct=0.20, daily_loss_cap_usd=500)
    mgr = RiskManager(limits, wallet_usd=1000.0)
    mgr.set_equity(800.0)  # 20% DD from peak 1000 → trip
    assert mgr.state.circuit_breaker_active is True
    peak_before = mgr.state.peak_equity_usd

    with caplog.at_level(logging.WARNING, logger="trendalgo.risk.manager"):
        mgr.reset_breaker(confirm=True, operator="owner")
    assert mgr.state.circuit_breaker_active is False
    assert mgr.state.peak_equity_usd == peak_before
    assert "reset by owner" in caplog.text

    # 5% recovery from trough → under threshold; entries stay enabled.
    mgr.set_equity(840.0)
    assert mgr.state.circuit_breaker_active is False
    assert mgr.can_open_trade() == (True, "ok")

    # Further drop back to 20% from original peak trips again.
    mgr.set_equity(800.0)
    assert mgr.state.circuit_breaker_active is True


def test_reset_peak_equity_is_separate() -> None:
    mgr = RiskManager(RiskLimits(circuit_breaker_drawdown_pct=0.10), wallet_usd=1000.0)
    mgr.set_equity(800.0)
    mgr.reset_breaker(confirm=True, operator="owner")
    assert mgr.state.peak_equity_usd == 1000.0
    mgr.reset_peak_equity(confirm=True, operator="owner")
    assert mgr.state.peak_equity_usd == 800.0


def test_reset_peak_needs_confirm_and_operator() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=1000.0)
    with pytest.raises(ValueError, match="confirm"):
        mgr.reset_peak_equity(confirm=False, operator="owner")
    with pytest.raises(ValueError, match="operator"):
        mgr.reset_peak_equity(confirm=True, operator="  ")
