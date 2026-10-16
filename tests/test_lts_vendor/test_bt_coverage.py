"""Every valid strategy row reaches its coin; signed edge and Vol Δ% ride the same publish path."""

from __future__ import annotations

from typing import Any

from trendalgo.lts_vendor.bridge import merge_backtest_into_coins
from trendalgo.lts_vendor.chart_closes import attach_chart_closes
from trendalgo.market.types import OhlcvPoint


def _strategy(symbol: str, indicator: str, net: float, timeframe: str = "1h") -> dict[str, Any]:
    return {
        "symbol": symbol,
        "indicator": indicator,
        "timeframe": timeframe,
        "params": {},
        "trailing_stop_pct": 8.0,
        "final_equity": 1000.0 + net,
        "net_pct": net,
        "trades": 14,
        "win_pct": 61.0,
        "total_runs": 20,
        "stops_tested": 5,
    }


def _summary() -> dict[str, Any]:
    names = ["SMA Crossover", "RSI", "MACD", "EMA Crossover", "Bollinger %B", "Heikin Ashi", "ATR"]
    nets = [230.5, 12.0, -3.0, 40.0, 90.0, 5.0, 7.0]
    results = [_strategy("QNT", name, net) for name, net in zip(names, nets, strict=True)]
    results.append(
        {
            "symbol": "QNT",
            "indicator": "B&H",
            "timeframe": "1h",
            "params": {},
            "trailing_stop_pct": None,
            "final_equity": 1.0,
            "net_pct": 273.5,
            "trades": "-",
            "win_pct": "-",
        }
    )
    results.append(_strategy("SUI", "RSI", 20.0))
    return {"results": results}


def test_merge_keeps_every_strategy_row_and_signed_edge() -> None:
    coins: list[dict[str, Any]] = [{"symbol": "QNT"}, {"symbol": "SUI"}, {"symbol": "NOPE"}]
    merge_backtest_into_coins(coins, _summary())
    qnt, sui, nope = coins

    assert len(qnt["backtest_top_strategies"]) == 7  # not capped at the old top 5
    assert qnt["backtest_buy_hold"]["net_pct"] == 273.5
    assert round(qnt["bot_vs_bh_pct"], 2) == -43.0  # bot trailed B&H: negative stays visible
    assert qnt["bot_best_label"] == "SMA Crossover 1h"

    assert sui["backtest_top_strategies"]
    assert sui["backtest_buy_hold"] is None
    assert "bot_vs_bh_pct" not in sui

    assert nope["backtest_top_strategies"] == []
    assert nope["backtest_buy_hold"] is None


def test_attach_chart_closes_sets_vol_delta_from_the_same_hourly_fetch() -> None:
    start = 1_700_000_000
    volumes = [100.0] * 216 + [200.0] * 24
    hourly = [
        OhlcvPoint(
            time=start + i * 3600,
            open=1.0,
            high=1.0,
            low=1.0,
            close=1.0 + i * 0.001,
            volume=volume,
        )
        for i, volume in enumerate(volumes)
    ]
    daily = [
        OhlcvPoint(
            time=start + d * 86400, open=1.0, high=1.0, low=1.0, close=1.0 + d * 0.01, volume=1.0
        )
        for d in range(30)
    ]

    def fake_fetch(
        pair: str, timeframe: str, since: object, until: object, **_kw: object
    ) -> list[OhlcvPoint]:
        return hourly if timeframe == "1h" else daily

    coins: list[dict[str, Any]] = [{"symbol": "SUI"}]
    attach_chart_closes(coins, lambda symbol: f"{symbol}/USD", fetch_ohlcv=fake_fetch)
    coin = coins[0]

    assert round(coin["volume_acceleration_pct"], 2) == 100.0
    assert coin["volume_acceleration_window_days"] == 7
    assert len(coin["closes_1h"]) == 240
    assert coin["ohlcv_source"] == "kraken"


def test_failed_hourly_fetch_leaves_no_stale_volume_keys() -> None:
    coins: list[dict[str, Any]] = [{"symbol": "SUI", "volume_acceleration_pct": 5.0}]
    attach_chart_closes(coins, lambda symbol: f"{symbol}/USD", fetch_ohlcv=lambda *_a, **_k: [])
    assert "volume_acceleration_pct" not in coins[0]
