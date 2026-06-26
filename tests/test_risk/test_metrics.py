from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager
from trendalgo.risk.metrics import metrics_summary


def test_metrics_summary() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=1000)
    mgr.record_pnl(25)
    m = metrics_summary(mgr, open_exposure_usd=100)
    assert m["equity_usd"] == 1025.0
    assert m["daily_pnl_usd"] == 25.0
    assert m["open_exposure_usd"] == 100.0
    assert m["can_trade"] is True
