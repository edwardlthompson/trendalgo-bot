from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

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


def _ok_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_detect_chat_id_deletes_webhook_then_reads_updates() -> None:
    tg = TelegramCommands(token="123:ABC", chat_id=None)
    calls: list[str] = []

    def fake_urlopen(req: object, timeout: float = 0) -> MagicMock:
        url = str(getattr(req, "full_url", req))
        calls.append(url)
        if url.endswith("/deleteWebhook"):
            return _ok_response({"ok": True, "result": True})
        if url.endswith("/getUpdates"):
            return _ok_response(
                {
                    "ok": True,
                    "result": [
                        {"message": {"chat": {"id": 42, "type": "private"}, "text": "/start"}}
                    ],
                }
            )
        raise URLError("unexpected")

    with patch("trendalgo.notifications.telegram.request.urlopen", side_effect=fake_urlopen):
        assert tg.detect_chat_id() == "42"
    assert any(u.endswith("/deleteWebhook") for u in calls)
    assert any(u.endswith("/getUpdates") for u in calls)
    assert calls.index(next(u for u in calls if u.endswith("/deleteWebhook"))) < calls.index(
        next(u for u in calls if u.endswith("/getUpdates"))
    )


def test_detect_chat_id_returns_none_when_delete_webhook_fails() -> None:
    tg = TelegramCommands(token="bad:token", chat_id=None)

    def fake_urlopen(req: object, timeout: float = 0) -> MagicMock:
        raise URLError("unauthorized")

    with patch("trendalgo.notifications.telegram.request.urlopen", side_effect=fake_urlopen):
        assert tg.detect_chat_id() is None


def test_api_url_builds_delete_webhook() -> None:
    tg = TelegramCommands(token="1:tok", chat_id=None)
    assert tg.api_url("deleteWebhook") == "https://api.telegram.org/bot1:tok/deleteWebhook"
