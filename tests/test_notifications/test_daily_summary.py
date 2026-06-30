"""Daily summary notification formatter."""

from __future__ import annotations

from trendalgo.notifications.daily_summary import format_daily_summary


def test_format_daily_summary_positive_day() -> None:
    text = format_daily_summary(
        {
            "net_worth_usd": 12_345.67,
            "daily_pnl_usd": 250.0,
            "daily_pnl_pct": 0.03,
            "health_score": 88,
            "allocation": [{"asset": "BTC", "pct": 0.5}],
        }
    )
    assert "Net worth: $12,345.67" in text
    assert "BTC leading gains" in text


def test_format_daily_summary_negative_day() -> None:
    text = format_daily_summary(
        {
            "net_worth_usd": 1000.0,
            "daily_pnl_usd": -10.0,
            "daily_pnl_pct": -0.01,
            "health_score": 50,
            "allocation": [],
        }
    )
    assert "Consider rebalancing" in text
