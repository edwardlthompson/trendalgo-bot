"""Telegram alert OHLC / strategy table extraction."""

from __future__ import annotations

from trendalgo.notifications.telegram_alert_data import strategy_table_rows


def test_strategy_table_omits_settings_column() -> None:
    rows = strategy_table_rows(
        {
            "strategies": [
                {
                    "name": "RVI",
                    "timeframe": "3h",
                    "params": "period=14",
                    "net_pct": 3.4,
                    "trades": 2,
                    "win_pct": 50.0,
                }
            ],
            "buy_hold": {"timeframe": "3h", "net_pct": 1.0},
        }
    )
    assert rows[0] == ["Indicator", "TF", "Net %", "Trades", "Win %"]
    assert "Settings" not in rows[0]
    assert all(len(r) == 5 for r in rows)
    assert rows[1][0] == "RVI"
    assert rows[-1][0] == "B&H"
