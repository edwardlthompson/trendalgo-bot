"""Enter-coin enrich: strategy table + OHLC-window trade indices."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from trendalgo.notifications import telegram_alert_enrich as enrich
from trendalgo.notifications.telegram_alert_enrich import enrich_enter_coin
from trendalgo.notifications.telegram_alert_image import build_enter_alert_png
from trendalgo.notifications.telegram_chart import enter_alert_png


def _frame(n: int = 40) -> pd.DataFrame:
    end = datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)
    idx = pd.DatetimeIndex([end - timedelta(hours=n - 1 - i) for i in range(n)], tz="UTC")
    close = pd.Series([100.0 + i * 0.5 for i in range(n)], index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


def _coin() -> dict[str, Any]:
    return {
        "symbol": "BTC/USD",
        "exchange": "kraken",
        "backtest_top_strategies": [
            {
                "indicator": "Secret Sauce Lab",
                "timeframe": "1h",
                "net_pct": 12.0,
                "trades": 3,
                "win_pct": 66.0,
            },
            {"indicator": "RVI", "timeframe": "1h", "net_pct": 4.0, "trades": 2, "win_pct": 50.0},
            {"indicator": "B&H", "timeframe": "1h", "net_pct": 1.0},
        ],
        "backtest_buy_hold": {"timeframe": "1h", "net_pct": 1.0},
    }


def test_enrich_stamps_strategies_and_in_range_trades() -> None:
    frame = _frame(50)
    regions = [
        {
            "entry_index": 10,
            "exit_index": 20,
            "entry_price": float(frame["close"].iloc[10]),
            "exit_price": float(frame["close"].iloc[20]),
            "pnl_pct": 5.0,
            "entry_time": frame.index[10],
            "exit_time": frame.index[20],
        },
        {
            "entry_index": 25,
            "exit_index": 30,
            "entry_price": float(frame["close"].iloc[25]),
            "exit_price": float(frame["close"].iloc[30]),
            "pnl_pct": -2.0,
            "entry_time": frame.index[25],
            "exit_time": frame.index[30],
        },
    ]
    with (
        patch(
            "trendalgo.notifications.telegram_alert_enrich.resolve_ohlcv_frame",
            return_value=frame,
        ),
        patch(
            "trendalgo.notifications.telegram_alert_enrich.regions_for_strategy",
            return_value=regions,
        ),
    ):
        out = enrich_enter_coin(_coin())
    assert len(out["strategies"]) == 2
    assert out["strategies"][0]["name"] == "Secret Sauce Lab"
    assert out["buy_hold"]["net_pct"] == 1.0
    n = len(out["ohlc_1h"])
    assert n == 50
    trades = out["alert_trades"]
    assert len(trades) == 2
    for tr in trades:
        assert 0 <= tr["entry_index"] < n
        assert 0 <= tr["exit_index"] < n
        assert tr["exit_index"] > tr["entry_index"]


def test_enrich_fail_soft_keeps_caption_fields() -> None:
    with patch(
        "trendalgo.notifications.telegram_alert_enrich.resolve_ohlcv_frame",
        side_effect=RuntimeError("offline"),
    ):
        out = enrich_enter_coin(_coin())
    assert out["strategies"][0]["name"] == "Secret Sauce Lab"
    assert "alert_trades" not in out


def test_enrich_empty_frame_and_no_tradable() -> None:
    empty = pd.DataFrame()
    with patch(
        "trendalgo.notifications.telegram_alert_enrich.resolve_ohlcv_frame",
        return_value=empty,
    ):
        out = enrich_enter_coin(_coin())
    assert "alert_trades" not in out
    bare = enrich_enter_coin({"symbol": "X"})
    assert bare["symbol"] == "X"
    only_bh = enrich_enter_coin(
        {"backtest_top_strategies": [{"indicator": "B&H", "net_pct": 1.0, "timeframe": "1h"}]}
    )
    assert "alert_trades" not in only_bh


def test_enrich_regions_exception_still_writes_ohlc() -> None:
    frame = _frame(25)
    with (
        patch(
            "trendalgo.notifications.telegram_alert_enrich.resolve_ohlcv_frame",
            return_value=frame,
        ),
        patch(
            "trendalgo.notifications.telegram_alert_enrich.regions_for_strategy",
            side_effect=RuntimeError("sim boom"),
        ),
    ):
        out = enrich_enter_coin(_coin())
    assert len(out["ohlc_1h"]) == 25
    assert out["alert_trades"] == []


def test_trades_from_regions_time_and_price_fallback() -> None:
    frame = _frame(20)
    stamp = frame.index[7]
    regions = [
        {"entry_price": "bad"},  # skipped
        {
            "entry_price": float(frame["close"].iloc[7]),
            "exit_price": float(frame["close"].iloc[12]),
            "pnl_pct": 1.0,
            "entry_time": stamp,
            "exit_time": frame.index[12],
        },
        {
            "entry_price": float(frame["close"].iloc[3]),
            "exit_price": float(frame["close"].iloc[3]),
            "pnl_pct": 0.0,
            "entry_index": 3,
            "exit_index": 3,  # forced xi bump
        },
    ]
    trades = enrich._trades_from_regions(regions, frame)
    assert len(trades) == 2
    assert trades[0]["entry_index"] == 7
    assert trades[1]["exit_index"] == 4


def test_coerce_and_bar_index_edges() -> None:
    assert enrich._coerce_index(True, 10) is None
    assert enrich._coerce_index(None, 10) is None
    assert enrich._coerce_index("nope", 10) is None
    assert enrich._coerce_index(99, 10) is None
    assert enrich._coerce_index("3", 10) == 3
    assert enrich._bar_index(None, [], [], 1.0) is None
    frame = _frame(5)
    assert enrich._bar_index(object(), list(frame.index), frame["close"].tolist(), 100.0) == 0


def test_enter_png_draws_when_trades_present() -> None:
    frame = _frame(30)
    regions = [
        {
            "entry_index": 5,
            "exit_index": 12,
            "entry_price": 102.0,
            "exit_price": 108.0,
            "pnl_pct": 5.0,
        }
    ]
    with (
        patch(
            "trendalgo.notifications.telegram_alert_enrich.resolve_ohlcv_frame",
            return_value=frame,
        ),
        patch(
            "trendalgo.notifications.telegram_alert_enrich.regions_for_strategy",
            return_value=regions,
        ),
    ):
        coin = enrich_enter_coin(_coin())
    png = enter_alert_png(coin) or build_enter_alert_png(coin)
    if png is not None:
        assert png[:4] == b"\x89PNG"
        assert len(coin["alert_trades"]) >= 1


def test_send_telegram_enriches_enter() -> None:
    from trendalgo.device.scan_alerts import _send_telegram
    from trendalgo.device.scanner_alert_diff import AlertEvent

    coin = _coin()
    client = MagicMock()
    client.enabled = True
    with patch(
        "trendalgo.device.scan_alerts.enrich_enter_coin",
        side_effect=lambda c: {**c, "alert_trades": [{"entry_index": 0, "exit_index": 1}]},
    ) as enrich_mock:
        with patch("trendalgo.device.scan_alerts.enter_alert_png", return_value=b"\x89PNG"):
            _send_telegram(
                AlertEvent(
                    kind="qualified_enter",
                    symbol="BTC/USD",
                    pair="BTC/USD",
                    reason="Entered the qualified list",
                    coin=coin,
                ),
                client=client,
            )
    enrich_mock.assert_called_once()
    client.send_photo.assert_called_once()
