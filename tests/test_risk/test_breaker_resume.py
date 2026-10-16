"""R1: resume un-pauses entries but never clears a tripped circuit breaker."""

from __future__ import annotations

import logging

import pytest

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager


def _tripped() -> RiskManager:
    limits = RiskLimits(circuit_breaker_drawdown_pct=0.10, daily_loss_cap_usd=500)
    mgr = RiskManager(limits, wallet_usd=1000)
    mgr.record_pnl(-150)  # 15% drawdown from a 1000 peak
    assert mgr.state.circuit_breaker_active is True
    return mgr


def test_the_breaker_survives_resume() -> None:
    mgr = _tripped()
    mgr.pause()
    mgr.resume()
    assert mgr.state.paused is False
    assert mgr.state.circuit_breaker_active is True
    assert mgr.can_open_trade() == (False, "circuit breaker active")


def test_reset_breaker_needs_explicit_confirmation() -> None:
    mgr = _tripped()
    with pytest.raises(ValueError, match="confirm"):
        mgr.reset_breaker(confirm=False, operator="owner")
    assert mgr.state.circuit_breaker_active is True


def test_reset_breaker_needs_a_named_operator() -> None:
    mgr = _tripped()
    with pytest.raises(ValueError, match="operator"):
        mgr.reset_breaker(confirm=True, operator="  ")
    assert mgr.state.circuit_breaker_active is True


def test_confirmed_reset_clears_logs_and_measures_drawdown_from_here(
    caplog: pytest.LogCaptureFixture,
) -> None:
    mgr = _tripped()
    with caplog.at_level(logging.WARNING, logger="trendalgo.risk.manager"):
        mgr.reset_breaker(confirm=True, operator="owner")
    assert mgr.state.circuit_breaker_active is False
    assert mgr.can_open_trade() == (True, "ok")
    assert "reset by owner" in caplog.text
    # The peak moves to current equity, so a small new loss does not re-trip on the old peak.
    mgr.record_pnl(-20)
    assert mgr.state.circuit_breaker_active is False
