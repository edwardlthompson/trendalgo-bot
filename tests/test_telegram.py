from trendalgo.api.risk import get_risk_status
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager
from trendalgo.notifications.telegram import TelegramCommands


def test_get_risk_status() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=500)
    status = get_risk_status(mgr)
    assert status["wallet_usd"] == 500


def test_telegram_commands() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=1000)
    tg = TelegramCommands(token=None, chat_id=None)
    assert tg.enabled is False
    text = tg.handle("status", mgr)
    assert "equity" in text.lower()
    tg.handle("pause", mgr)
    assert mgr.state.paused is True
