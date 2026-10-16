from trendalgo.api.risk import get_risk_status
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager


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


def test_telegram_resume_is_refused_and_leaves_the_pause_in_place() -> None:
    # H6: Telegram can pause and nothing else.
    mgr = RiskManager(RiskLimits(), wallet_usd=1000)
    tg = TelegramCommands(token=None, chat_id=None)
    tg.handle("pause", mgr)
    reply = tg.handle("resume", mgr)
    assert "refused" in reply.lower()
    assert mgr.state.paused is True
    assert tg.handle("/help", mgr) == (
        "Commands: status, pause. Resume and breaker reset are host-only."
    )


def test_telegram_breaker_reset_is_refused() -> None:
    mgr = RiskManager(RiskLimits(), wallet_usd=1000)
    mgr.state.circuit_breaker_active = True
    tg = TelegramCommands(token=None, chat_id=None)
    for command in ("/reset_breaker", "reset_breaker", "/reset", "reset"):
        assert "refused" in tg.handle(command, mgr).lower()
    assert mgr.state.circuit_breaker_active is True
