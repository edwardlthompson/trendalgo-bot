from datetime import UTC, datetime, timedelta

import pytest

from trendalgo.notifications.grokbot_filter import event_allowed
from trendalgo.notifications.grokbot_golive import build_golive_report, journal_stats


def test_journal_stats_drawdown_and_losing_streak() -> None:
    rows = [
        {"side": "sell", "pnl_usd": -2, "created_at": "2026-11-15T03:00:00+00:00"},
        {"side": "sell", "pnl_usd": -1, "created_at": "2026-11-15T02:00:00+00:00"},
        {"side": "sell", "pnl_usd": 5, "created_at": "2026-11-15T01:00:00+00:00"},
        {"side": "buy", "pnl_usd": 0, "created_at": "2026-11-15T00:00:00+00:00"},
    ]
    stats = journal_stats(rows)
    assert stats["trade_count"] == 4
    assert stats["sell_count"] == 3
    assert stats["pnl_usd"] == 2.0
    assert stats["max_losing_streak"] == 2
    assert stats["current_losing_streak"] == 2
    assert stats["max_drawdown_usd"] == 3.0


def test_journal_stats_losing_book_drawdown_pct() -> None:
    rows = [
        {
            "side": "sell",
            "pnl_usd": -20,
            "stake_usd": 100,
            "created_at": "2026-11-15T02:00:00+00:00",
        },
        {
            "side": "sell",
            "pnl_usd": -10,
            "stake_usd": 100,
            "created_at": "2026-11-15T01:00:00+00:00",
        },
    ]
    stats = journal_stats(rows)
    assert stats["pnl_usd"] == -30.0
    assert stats["max_drawdown_usd"] == 30.0
    assert stats["max_drawdown_pct"] == 0.15
    report = build_golive_report(trades=rows)
    assert "drawdown over 10%" in report["hints"]
    assert "dry-run sample looks populated" not in " ".join(report["hints"])


def test_golive_report_is_advisory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    monkeypatch.setenv("BACKTEST_FEE_BPS_ROUND_TRIP", "40")
    now = datetime(2026, 11, 15, tzinfo=UTC)
    old = (now - timedelta(days=10)).isoformat()
    report = build_golive_report(
        trades=[{"side": "sell", "pnl_usd": 1, "created_at": old}],
        now=now,
    )
    assert report["advisory"] is True
    assert report["bypasses_go_live_gate"] is False
    assert report["fee_assumptions"]["backtest_fee_bps_round_trip"] == 40.0
    assert "synthetic" in " ".join(report["stale"]["warnings"])
    assert "few dry-run trades" in report["hints"]


def test_golive_filter_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "golive")
    assert event_allowed("golive_readiness") is True
    assert event_allowed("sweep_complete") is False


def test_golive_api_get(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from pathlib import Path

    from tests.support.api_client import make_api_client

    root = Path(str(tmp_path))
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(root))
    client = make_api_client()
    body = client.get("/api/v1/notifications/golive-readiness").json()
    assert body["advisory"] is True
    assert body["bypasses_go_live_gate"] is False
    assert body["trade_count"] == 0
