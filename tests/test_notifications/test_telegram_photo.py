"""Telegram send_photo multipart smoke (no network)."""

from __future__ import annotations

from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.notifications.telegram_chart import chart_png_bytes, closes_from_coin


def test_send_photo_disabled_without_creds() -> None:
    tg = TelegramCommands(token=None, chat_id=None)
    assert tg.send_photo(b"\x89PNG", "hi") is False


def test_chart_png_from_closes() -> None:
    png = chart_png_bytes([1.0, 1.1, 1.05, 1.2], title="ETH")
    # matplotlib may be absent in minimal envs
    if png is not None:
        assert png[:4] == b"\x89PNG"


def test_closes_from_coin() -> None:
    assert closes_from_coin({"closes_7d": [1, 2, "x", 3]}) == [1.0, 2.0, 3.0]
