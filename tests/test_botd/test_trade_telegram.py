"""Host Telegram secrets + fill notify path."""

from __future__ import annotations

from pathlib import Path

from trendalgo.botd.fills import FillsLedger
from trendalgo.botd.telegram_secrets import load_creds, save_creds, save_notify_flags
from trendalgo.botd.trade_notify import notify_fill
from trendalgo.notifications.telegram import TelegramCommands


class _FakeTg(TelegramCommands):
    def __init__(self) -> None:
        super().__init__(token="t", chat_id="1")
        self.sent: list[str] = []

    def send_message(self, text: str) -> bool:
        self.sent.append(text)
        return True


def test_host_secrets_roundtrip(tmp_path: Path) -> None:
    save_creds(tmp_path, bot_token="tok", chat_id="99")
    token, chat = load_creds(tmp_path)
    assert token == "tok"
    assert chat == "99"


def test_notify_fill_respects_prefs(tmp_path: Path) -> None:
    save_creds(tmp_path, bot_token="tok", chat_id="1")
    save_notify_flags(tmp_path, trade_alerts=False, telegram_enabled=True, telegram_trades=True)
    fake = _FakeTg()
    assert (
        notify_fill(
            tmp_path,
            pair="ETH/USD",
            side="buy",
            amount=1,
            price=2,
            client=fake,
        )
        is False
    )
    assert fake.sent == []
    save_notify_flags(tmp_path, trade_alerts=True, telegram_enabled=True, telegram_trades=True)
    assert notify_fill(
        tmp_path,
        pair="ETH/USD",
        side="buy",
        amount=1,
        price=2,
        client=fake,
    )
    assert fake.sent and "ETH/USD" in fake.sent[0]


def test_fills_ledger_calls_hook(tmp_path: Path) -> None:
    seen: list[str] = []

    def hook(**kwargs: object) -> None:
        seen.append(str(kwargs.get("pair")))

    ledger = FillsLedger(
        tmp_path / "fills.db",
        host_owner_id="owner",
        secrets_root=tmp_path,
        on_live_fill=hook,
    )
    ledger.record(
        owner_id="owner",
        live=True,
        plan_version=1,
        bundle_hash="h",
        pair="AAA/USD",
        side="sell",
        amount=1,
        price=2,
        filled_at="2026-10-13T00:00:00+00:00",
    )
    assert seen == ["AAA/USD"]
    ledger.record(
        owner_id="owner",
        live=False,
        plan_version=1,
        bundle_hash="h",
        pair="BBB/USD",
        side="buy",
        amount=1,
        price=2,
        filled_at="2026-10-13T00:00:01+00:00",
    )
    assert seen == ["AAA/USD"]
