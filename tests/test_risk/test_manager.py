from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager


def test_compute_stake_caps() -> None:
    mgr = RiskManager(RiskLimits(max_stake_usd=100, max_stake_pct=0.02), wallet_usd=1000)
    assert mgr.compute_stake(500) == 20.0
    assert mgr.compute_stake(15) == 15.0


def test_daily_loss_cap() -> None:
    mgr = RiskManager(RiskLimits(daily_loss_cap_usd=50), wallet_usd=1000)
    mgr.record_pnl(-60)
    ok, reason = mgr.can_open_trade()
    assert ok is False
    assert "daily loss" in reason


def test_circuit_breaker() -> None:
    mgr = RiskManager(RiskLimits(circuit_breaker_drawdown_pct=0.10), wallet_usd=1000)
    mgr.state.peak_equity_usd = 1000
    mgr.record_pnl(-150)
    assert mgr.state.circuit_breaker_active is True
    assert mgr.can_open_trade()[0] is False


def test_pause_resume() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=1000)
    mgr.pause()
    assert mgr.can_open_trade()[0] is False
    mgr.resume()
    assert mgr.can_open_trade()[0] is True
