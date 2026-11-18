"""LTS-shaped Telegram captions and keyboard."""

from __future__ import annotations

import json
from typing import Any
from urllib import parse

from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.notifications.telegram_format import format_qualified_enter, format_watchlist_leave
from trendalgo.notifications.telegram_keyboard import context_keyboard, reply_markup_json


def _lts_coin() -> dict[str, Any]:
    return {
        "symbol": "XLM",
        "name": "Stellar",
        "pair": "XLM/USD",
        "gains": {"7d": 12.5, "30d": 40.0},
        "health_score": 72.0,
        "uniformity_score": 58.0,
        "volume_24h": 2_900_000.0,
        "listed_on": ["kraken"],
        "exchange_volumes": {"kraken": 1_200_000.0},
        "cmc_slug": "stellar",
        "current_rank": 12,
    }


def test_enter_caption_uses_lts_fields_not_dashes() -> None:
    text = format_qualified_enter(_lts_coin())
    assert "—" not in text.split("Exchange")[0]
    assert "+12.5%" in text
    assert "+40.0%" in text
    assert "72" in text
    assert "58" in text
    assert "<a href=" in text


def test_enter_caption_omits_strategy_table() -> None:
    coin = {
        **_lts_coin(),
        "strategies": [
            {"name": "RVI", "pnl_pct": 3.4, "vs_bh": 1.2},
            {"name": "EMA", "pnl_pct": 2.1, "vs_bh": 0.5},
        ],
        "best_bt": "RVI",
    }
    text = format_qualified_enter(coin)
    assert "Strategy" not in text
    assert "RVI" not in text
    assert "Best BT" not in text


def test_enter_caption_skips_empty_exchange_volumes() -> None:
    coin = {
        **_lts_coin(),
        "listed_on": ["kraken", "coinbase"],
        "exchange_volumes": {},
        "volume_24h": 0,
    }
    text = format_qualified_enter(coin)
    assert "Exchange Volumes" not in text
    assert "No volume" not in text
    assert "Total 24h Volume: —" in text


def test_leave_caption_includes_reason_and_lifecycle() -> None:
    coin = {
        **_lts_coin(),
        "exit_reason": "7d gain below threshold",
        "lifecycle_pnl_pct": 8.5,
        "held_days": 3,
    }
    text = format_watchlist_leave(symbol="XLM", reason="7d gain below threshold", coin=coin)
    assert "has left the qualified list" in text
    assert "7d gain below threshold" in text
    assert "Lifecycle:" in text
    assert "Held 3d" in text


def test_keyboard_has_view_analyze_and_kraken() -> None:
    kb = context_keyboard(_lts_coin())
    flat = [btn for row in kb["inline_keyboard"] for btn in row]
    labels = [b["text"] for b in flat]
    assert any("View Chart" in t for t in labels)
    assert any("Analyze" in t for t in labels)
    assert "Kraken" in labels
    assert "tradingview.com" in flat[0]["url"]
    assert "coinmarketcap.com" in flat[1]["url"]


def test_send_photo_multipart_includes_parse_mode_and_markup(monkeypatch: Any) -> None:
    captured: dict[str, bytes] = {}

    class _Resp:
        status = 200

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float = 0) -> _Resp:  # noqa: ARG001
        captured["body"] = req.data
        captured["ctype"] = req.headers.get("Content-type") or req.headers.get("Content-Type") or ""
        return _Resp()

    monkeypatch.setattr("trendalgo.notifications.telegram.request.urlopen", fake_urlopen)
    tg = TelegramCommands(token="t", chat_id="1")
    markup = reply_markup_json(_lts_coin())
    assert tg.send_photo(
        b"\x89PNG\r\n\x1a\nxxxx", "<b>hi</b>", parse_mode="HTML", reply_markup=markup
    )
    body = captured["body"].decode("utf-8", errors="replace")
    assert "parse_mode" in body
    assert "HTML" in body
    assert "reply_markup" in body
    assert "inline_keyboard" in body


def test_send_message_urlencodes_markup(monkeypatch: Any) -> None:
    captured: dict[str, str] = {}

    class _Resp:
        status = 200

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    def fake_urlopen(req: Any, timeout: float = 0) -> _Resp:  # noqa: ARG001
        captured["q"] = req.data.decode()
        return _Resp()

    monkeypatch.setattr("trendalgo.notifications.telegram.request.urlopen", fake_urlopen)
    tg = TelegramCommands(token="t", chat_id="1")
    markup = context_keyboard(_lts_coin())
    assert tg.send_message("hi", parse_mode="HTML", reply_markup=markup)
    q = parse.parse_qs(captured["q"])
    assert q["parse_mode"] == ["HTML"]
    assert "inline_keyboard" in json.loads(q["reply_markup"][0])
