"""Grok Bot webhook: payload, disabled default, filter, cooldown, Telegram-first."""

from __future__ import annotations

from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import BaseHandler, Request, build_opener

import pytest

from trendalgo.botd.telegram_secrets import save_creds, save_notify_flags
from trendalgo.botd.trade_notify import notify_fill
from trendalgo.notifications import grokbot as grokbot_mod
from trendalgo.notifications.grokbot import emit, grokbot_enabled, send_test, telegram_ai_note
from trendalgo.notifications.grokbot_cooldown import reset as reset_cooldown
from trendalgo.notifications.grokbot_filter import event_allowed
from trendalgo.notifications.grokbot_payload import scanner_alert_payload, trade_payload
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.risk.journal import TradeJournal
from trendalgo.strategies.runtime.contract import Candle, Position, Signal, StrategyContext
from trendalgo.trading.exit_explain import describe_exit
from trendalgo.trading.runner.dry_run import DryRunRunner


@pytest.fixture(autouse=True)
def _reset_grok(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_cooldown()
    monkeypatch.delenv("GROKBOT_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("GROKBOT_WEBHOOK_KEY", raising=False)
    monkeypatch.delenv("GROKBOT_WEBHOOK_EVENTS", raising=False)
    monkeypatch.delenv("GROKBOT_WEBHOOK_COOLDOWN_SEC", raising=False)


def test_disabled_by_default() -> None:
    assert grokbot_enabled() is False
    assert (
        emit(trade_payload(pair="BTC/USD", side="buy", amount=1, price=2))["reason"] == "disabled"
    )


def test_http_url_is_not_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "http://example.invalid/hook")
    assert grokbot_enabled() is False


def test_trade_payload_has_strategy_rationale_and_exit_rule() -> None:
    payload = trade_payload(
        pair="ETH/USD",
        side="sell",
        amount=25.0,
        price=3000.0,
        realized_pnl_usd=1.5,
        strategy_id="macd-kraken-1h",
        rationale="macd cross up 1h kraken",
        exit_rule="MACD cross down",
        exchange="kraken",
    )
    assert payload["schema_version"] == "1"
    assert payload["event_type"] == "trade_exit"
    assert payload["strategy_id"] == "macd-kraken-1h"
    assert payload["exit_rule"] == "MACD cross down"
    assert payload["rationale"] == "macd cross up 1h kraken"
    assert payload["stake"] == 25.0
    assert payload["exit_price"] == 3000.0
    assert "api_key" not in payload


def test_event_filter_trades_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "trades")
    assert event_allowed("trade_entry") is True
    assert event_allowed("trade_exit") is True
    assert event_allowed("scanner_alert", tier="A") is False
    assert event_allowed("test") is True


def test_event_filter_scanner_a(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "scanner-a")
    assert event_allowed("scanner_alert", tier="A") is True
    assert event_allowed("scanner_alert", tier="B") is False
    assert event_allowed("trade_exit") is False


def test_filtered_emit_does_not_post(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "trades")
    posted: list[object] = []

    def boom(*_a: object, **_k: object) -> Any:
        posted.append(1)
        raise AssertionError("should not post")

    monkeypatch.setattr(grokbot_mod, "_urlopen", boom)
    result = emit(
        scanner_alert_payload(pair="BTC/USD", tier="A", uniformity=0.8, gain=0.06), wait=True
    )
    assert result["reason"] == "filtered"
    assert posted == []


class _FakeHTTPError(HTTPError):
    def __init__(self, code: int) -> None:
        super().__init__("https://example.invalid/hook", code, "quota", hdrs=None, fp=None)  # type: ignore[arg-type]


def test_non_2xx_marks_unavailable_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("GROKBOT_WEBHOOK_COOLDOWN_SEC", "60")
    hits = {"n": 0}

    def fail(_req: object, timeout: float = 0) -> Any:
        hits["n"] += 1
        raise _FakeHTTPError(429)

    monkeypatch.setattr(grokbot_mod, "_urlopen", fail)
    first = emit(trade_payload(pair="BTC/USD", side="buy", amount=1, price=2), wait=True)
    assert first["sent"] is False
    assert first.get("unavailable") is True
    assert hits["n"] == 1
    second = emit(trade_payload(pair="BTC/USD", side="sell", amount=1, price=2), wait=True)
    assert second["reason"] == "grok unavailable"
    assert hits["n"] == 1
    assert "AI brief unavailable" in telegram_ai_note("Trade BUY BTC/USD")


def test_redirect_handler_does_not_follow() -> None:
    from trendalgo.notifications.grokbot_http import NoRedirect

    req = Request(
        "https://example.invalid/hook",
        data=b"{}",
        headers={"Authorization": "Bearer secret-key"},
        method="POST",
    )
    followed = NoRedirect().redirect_request(
        req, None, 302, "Found", Message(), "http://evil.invalid/steal"
    )
    assert followed is None


def test_redirect_is_unavailable_and_does_not_hop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trendalgo.notifications.grokbot_http import NoRedirect

    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("GROKBOT_WEBHOOK_KEY", "secret-key")
    monkeypatch.setenv("GROKBOT_WEBHOOK_COOLDOWN_SEC", "60")
    hops: list[str] = []

    class _Once(BaseHandler):
        handler_order = 100

        def https_open(self, req: Request) -> Any:
            hops.append(str(req.full_url))
            hdrs = Message()
            hdrs["Location"] = "http://evil.invalid/steal"
            raise HTTPError(req.full_url, 302, "Found", hdrs, BytesIO())

        def http_open(self, req: Request) -> Any:
            hops.append(str(req.full_url))
            raise AssertionError("must not follow plaintext redirect")

        def close(self) -> None:
            return None

    def open_probe(req: Request, timeout: float = 0) -> Any:
        del timeout
        return build_opener(NoRedirect(), _Once()).open(req)

    monkeypatch.setattr(grokbot_mod, "_urlopen", open_probe)
    result = emit(trade_payload(pair="BTC/USD", side="buy", amount=1, price=2), wait=True)
    assert result["sent"] is False
    assert result.get("unavailable") is True
    assert hops == ["https://example.invalid/hook"]


def test_timeout_is_grok_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("GROKBOT_WEBHOOK_COOLDOWN_SEC", "60")

    def timeout(_req: object, timeout: float = 0) -> Any:
        raise URLError("timed out")

    monkeypatch.setattr(grokbot_mod, "_urlopen", timeout)
    result = send_test(wait=True)
    assert result["sent"] is False
    assert result.get("unavailable") is True


def test_notify_fill_sends_telegram_before_grokbot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    save_creds(tmp_path, bot_token="tok", chat_id="1")
    save_notify_flags(tmp_path, trade_alerts=True, telegram_enabled=True, telegram_trades=True)
    order: list[str] = []

    class _Tg(TelegramCommands):
        def __init__(self) -> None:
            super().__init__(token="t", chat_id="1")

        def send_message(self, text: str) -> bool:
            order.append("telegram")
            assert "ETH/USD" in text
            return True

    def fake_emit(_payload: dict[str, Any], **_k: Any) -> dict[str, Any]:
        order.append("grokbot")
        return {"sent": True, "queued": True}

    monkeypatch.setattr("trendalgo.botd.trade_notify.emit", fake_emit)
    sent = notify_fill(
        tmp_path,
        pair="ETH/USD",
        side="buy",
        amount=1,
        price=2,
        client=_Tg(),
        strategy_id="macd-kraken-1h",
        rationale="macd cross up 1h kraken",
    )
    assert sent is True
    assert order == ["telegram", "grokbot"]


def test_telegram_still_sends_when_grokbot_disabled(tmp_path: Path) -> None:
    save_creds(tmp_path, bot_token="tok", chat_id="1")
    save_notify_flags(tmp_path, trade_alerts=True, telegram_enabled=True, telegram_trades=True)

    class _Tg(TelegramCommands):
        def __init__(self) -> None:
            super().__init__(token="t", chat_id="1")
            self.sent: list[str] = []

        def send_message(self, text: str) -> bool:
            self.sent.append(text)
            return True

    tg = _Tg()
    assert notify_fill(tmp_path, pair="BTC/USD", side="sell", amount=1, price=2, client=tg) is True
    assert tg.sent and "BTC/USD" in tg.sent[0]


class _MacdExit:
    strategy_id = "macd-kraken-1h"
    timeframe = "1h"

    @property
    def dataframe(self) -> Any:
        import pandas as pd

        return pd.DataFrame({"close": [1.0], "macd": [0.0], "macd_signal": [0.0]})

    def on_candle(self, candle: Candle, ctx: StrategyContext) -> None:
        del candle, ctx

    def signal(self, ctx: StrategyContext) -> Signal | None:
        if ctx.position is None:
            return Signal(side="buy", stake_usd=10.0, rationale="macd cross up 1h kraken")
        return None

    def exit(self, ctx: StrategyContext, position: Position) -> bool:
        del ctx, position
        return True

    def explain_exit(self, ctx: StrategyContext, position: Position) -> str:
        del ctx, position
        return "MACD cross down"


def test_native_runner_records_exit_rule_without_notify(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "journal.db")
    runner = DryRunRunner(
        strategy=_MacdExit(),  # type: ignore[arg-type]
        journal=journal,
        pair="BTC/USD",
        exchange_id="kraken",
        fill_offset=0,
        notify=False,
    )
    runner.tick(Candle(1, 100, 100, 100, 100, 1))
    runner.tick(Candle(2, 101, 101, 101, 101, 1))
    rows = journal.list_trades(limit=10)
    exits = [r for r in rows if str(r["side"]) == "sell"]
    assert exits
    assert exits[0]["rationale"] == "MACD cross down"
    assert exits[0]["signal_source"] == "macd-kraken-1h"


def test_api_test_route_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    from tests.support.api_client import make_api_client

    client = make_api_client()
    status = client.get("/api/v1/notifications/grokbot").json()
    assert status["enabled"] is False
    result = client.post("/api/v1/notifications/grokbot/test").json()
    assert result["sent"] is False


def test_scanner_snapshot_posts_one_grokbot_event_per_opportunity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime

    from trendalgo.scanner.alerts import emit_alerts_for_snapshot
    from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
    from trendalgo.scanner.store import ScannerStore

    posted: list[str] = []

    def capture(payload: dict[str, Any], **_k: Any) -> dict[str, Any]:
        posted.append(str(payload.get("pair")))
        return {"sent": True, "queued": True}

    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setattr("trendalgo.notifications.grokbot.emit", capture)
    now = datetime.now(UTC)
    emit_alerts_for_snapshot(
        ScannerStore(tmp_path / "scanner.db"),
        QualifiedSnapshot(
            generated_at=now,
            as_of=now,
            scan_id=1,
            opportunities=[
                OpportunityRow(
                    rank=1,
                    pair="BTC/USD",
                    uniformity=0.8,
                    gain_pct=0.06,
                    volume_score=3,
                    entry_signal=True,
                )
            ],
        ),
    )
    assert posted == ["BTC/USD"]


def test_describe_exit_macd_label() -> None:
    import pandas as pd

    class _S:
        strategy_id = "macd-kraken-1h"

        def explain_exit(self, ctx: StrategyContext, position: Position) -> str:
            del ctx, position
            return "MACD cross down"

    ctx = StrategyContext(
        pair="BTC/USD",
        timeframe="1h",
        dataframe=pd.DataFrame({"macd": [1.0, 0.0], "macd_signal": [0.0, 0.5]}),
    )
    pos = Position(pair="BTC/USD", side="buy", stake_usd=10, entry_price=100)
    assert describe_exit(_S(), ctx, pos) == "MACD cross down"
