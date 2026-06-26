from trendalgo.risk.config import RiskLimits
from trendalgo.risk.strategy_mixins import RiskGuardMixin, ScalePositionMixin


class _StubStrategy(RiskGuardMixin):
    pass


class _ScaleStub(ScalePositionMixin):
    pass


def test_scale_position_mixin() -> None:
    stub = _ScaleStub()
    stub.exit_scale_out_enabled = True
    trade = type("T", (), {"stake_amount": 100})()
    delta = stub.adjust_trade_position(trade, None, 100, 0.05, 10, None, 90, 100, 0.05, 0.05)
    assert delta == -50.0
    assert stub.custom_stoploss("BTC/USD", trade, None, 100, 0.02) == -0.03


def test_risk_custom_stake_when_paused() -> None:
    strat = _StubStrategy()
    strat.risk_manager = None
    strat.risk_limits = RiskLimits(max_stake_usd=50)
    strat._ensure_risk_manager(wallet_usd=1000)
    assert strat.risk_manager is not None
    strat.risk_manager.pause()
    assert (
        strat.risk_custom_stake_amount("BTC/USD", None, 50000, 100, None, None, 1, None, "long")
        == 0.0
    )


def test_risk_custom_stake_capped() -> None:
    strat = _StubStrategy()
    assert (
        strat.risk_custom_stake_amount("BTC/USD", None, 50000, 500, None, None, 1, None, "long")
        == 20.0
    )
