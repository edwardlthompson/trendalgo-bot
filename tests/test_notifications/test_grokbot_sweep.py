import pytest

from trendalgo.notifications.grokbot_filter import event_allowed
from trendalgo.notifications.grokbot_sweep import overfitting_flags, sweep_digest


def test_sweep_digest_flags_thin_high_win() -> None:
    coins = [
        {
            "symbol": "DOGE",
            "backtest_top_strategies": [
                {
                    "indicator": "RSI",
                    "trades": 3,
                    "win_pct": 100,
                    "net_pct": 12,
                    "confidence_score": 20,
                }
            ],
        },
        {
            "symbol": "BTC",
            "backtest_top_strategies": [
                {
                    "indicator": "MACD",
                    "trades": 20,
                    "win_pct": 55,
                    "net_pct": 4,
                    "confidence_score": 70,
                }
            ],
        },
    ]
    digest = sweep_digest(coins)
    assert digest["coin_count"] == 2
    assert digest["oos_split"] is None
    assert digest["top"][0]["symbol"] == "DOGE"
    assert "thin_sample" in digest["overfitting"][0]["flags"]
    assert overfitting_flags({"trades": 3, "win_pct": 100}) == [
        "thin_sample",
        "high_win_thin_sample",
    ]


def test_emit_sweep_complete_skips_without_summary() -> None:
    from trendalgo.notifications.grokbot_sweep import emit_sweep_complete

    assert emit_sweep_complete([{"symbol": "BTC"}], None) is None


def test_sweep_filter_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "sweep")
    assert event_allowed("sweep_complete") is True
    assert event_allowed("weekly_digest") is False
