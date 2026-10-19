"""Signed Bot vs Buy & Hold edge (negative values must survive)."""

from __future__ import annotations

from trendalgo.scanner.backtest_edge import bot_vs_bh_edge


def _row(indicator: str, net: float, timeframe: str = "1h") -> dict[str, object]:
    return {"indicator": indicator, "timeframe": timeframe, "net_pct": net}


def test_bot_beating_buy_and_hold_is_positive() -> None:
    edge = bot_vs_bh_edge(
        [_row("RSI", 51.7), _row("Bollinger %B", 99.4, "4h")],
        {"indicator": "B&H", "net_pct": 25.1},
    )
    assert edge is not None
    assert edge["bot_vs_bh_pct"] == round(99.4 - 25.1, 6)
    assert edge["bot_best_label"] == "Bollinger %B 4h"


def test_bot_trailing_buy_and_hold_is_negative_not_hidden() -> None:
    edge = bot_vs_bh_edge(
        [_row("SMA Crossover", 230.5), _row("EMA Crossover", 108.2)],
        {"indicator": "B&H", "net_pct": 273.5},
    )
    assert edge is not None
    assert edge["bot_vs_bh_pct"] < 0
    assert round(edge["bot_vs_bh_pct"], 2) == -43.0


def test_buy_and_hold_rows_are_not_counted_as_the_bot() -> None:
    edge = bot_vs_bh_edge(
        [_row("B&H", 500.0), _row("RSI", 12.0)],
        {"indicator": "B&H", "net_pct": 40.0},
    )
    assert edge is not None
    assert edge["bot_best_net_pct"] == 12.0
    assert edge["bot_vs_bh_pct"] == -28.0


def test_oracle_max_is_not_counted_as_best_bot() -> None:
    edge = bot_vs_bh_edge(
        [_row("Oracle max", 500.0), _row("RSI", 12.0), _row("Secret Sauce", 40.0)],
        {"indicator": "B&H", "net_pct": 25.0},
    )
    assert edge is not None
    assert edge["bot_best_net_pct"] == 40.0
    assert edge["bot_best_label"] == "Secret Sauce 1h"
    assert edge["bot_vs_bh_pct"] == 15.0


def test_secret_sauce_can_win_best_bt() -> None:
    edge = bot_vs_bh_edge(
        [_row("Secret Sauce", 88.0), _row("RSI", 10.0)],
        {"indicator": "B&H", "net_pct": 20.0},
    )
    assert edge is not None
    assert edge["bot_best_net_pct"] == 88.0


def test_missing_buy_and_hold_or_strategies_yield_no_edge() -> None:
    assert bot_vs_bh_edge([_row("RSI", 5.0)], None) is None
    assert bot_vs_bh_edge([], {"net_pct": 5.0}) is None
    assert bot_vs_bh_edge([{"indicator": "RSI", "net_pct": float("nan")}], {"net_pct": 1.0}) is None
