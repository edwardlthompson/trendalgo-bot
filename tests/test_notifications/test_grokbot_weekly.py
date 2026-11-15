"""Weekly digest summary + filter alias."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trendalgo.notifications.grokbot_filter import event_allowed
from trendalgo.notifications.grokbot_weekly import build_weekly_digest, format_weekly_telegram


def test_weekly_digest_summarizes_trades_and_alerts() -> None:
    now = datetime(2026, 11, 15, tzinfo=UTC)
    since = (now - timedelta(days=2)).isoformat()
    digest = build_weekly_digest(
        trades=[
            {
                "pair": "BTC/USD",
                "side": "sell",
                "pnl_usd": 1.5,
                "signal_source": "macd-kraken-1h",
                "created_at": since,
            }
        ],
        alerts=[{"tier": "A", "pair": "BTC/USD", "created_at": since}],
        history=[
            {"kind": "qualified_enter", "pair": "ETH/USD", "at": since},
            {"kind": "watchlist_leave", "pair": "SOL/USD", "at": since},
        ],
        now=now,
    )
    assert digest["trade_count"] == 1
    assert digest["pnl_usd"] == 1.5
    assert digest["tier_counts"]["A"] == 1
    assert "ETH/USD" in digest["entered"]
    assert "SOL/USD" in digest["left"]
    text = format_weekly_telegram(digest)
    assert "TrendAlgo weekly" in text
    assert "macd-kraken-1h" in text


def test_weekly_filter_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "weekly")
    assert event_allowed("weekly_digest") is True
    assert event_allowed("trade_exit") is False
