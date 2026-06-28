"""Chart marker P/L percentage."""

from __future__ import annotations

from trendalgo.bots.chart_trades import trades_to_chart_markers


def test_sell_marker_includes_pnl_pct() -> None:
    trades = [
        {"side": "buy", "stake_usd": 100, "pnl_usd": 0, "created_at": "2026-01-01T00:00:00+00:00"},
        {"side": "sell", "stake_usd": 100, "pnl_usd": 12.5, "created_at": "2026-01-02T00:00:00+00:00"},
    ]
    markers = trades_to_chart_markers(trades)
    sell = [m for m in markers if m["side"] == "sell"][0]
    assert sell["pnl_usd"] == 12.5
    assert sell["pnl_pct"] == 12.5
