"""p2-lts-port: the closed-bar streaming port matches the LTS engine (L3, L4, L5, L7, L8)."""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import numpy as np
import pandas as pd
import pytest

from trendalgo.botd.lts_port.bar import Bar
from trendalgo.botd.lts_port.closed_signals import (
    MIN_LOOKBACK_BARS,
    drop_forming_bar,
    last_closed_signals,
)
from trendalgo.botd.lts_port.state import PortState
from trendalgo.botd.lts_port.trader import StreamingTrader
from trendalgo.lts_vendor.backtesting.engine import run_backtest
from trendalgo.lts_vendor.backtesting.models import BacktestConfig, Trade
from trendalgo.lts_vendor.backtesting.parameter_space import PARAMETER_SPACE
from trendalgo.lts_vendor.backtesting.signals import generate_indicator_signals

INDICATORS = ("RSI", "MACD", "Bollinger %B", "EMA Crossover", "SMA Crossover", "Heikin Ashi")
BARS = 200
CONFIGS: dict[str, BacktestConfig] = {
    "tsl_default": BacktestConfig(),
    "tsl_8": BacktestConfig(trailing_stop_loss_pct=8.0),
    "tp_fixed": BacktestConfig(take_profit_pct=3.0, trailing_stop_loss_pct=6.0),
    "tp_trailing": BacktestConfig(
        take_profit_pct=2.0, trailing_take_profit_pct=1.5, trailing_stop_loss_pct=4.0
    ),
    "tsl_off": BacktestConfig(trailing_stop_enabled=False),
    "fixed_usd": BacktestConfig(stake_mode="fixed_usd", stake_value=300.0),
    "percent": BacktestConfig(stake_mode="percent", stake_value=40.0),
}


def _walk(bars: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, bars)))
    high = close * (1.0 + np.abs(rng.normal(0.0, 0.004, bars)))
    low = close * (1.0 - np.abs(rng.normal(0.0, 0.004, bars)))
    open_ = np.concatenate(([close[0]], close[:-1]))
    volume = rng.uniform(1_000.0, 10_000.0, bars)
    index = pd.date_range("2026-09-01", periods=bars, freq="h", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=index
    )


def _flat(bars: int) -> pd.DataFrame:
    """Flat closes whose wicks never reach a 1% trailing stop, so only signals exit."""
    index = pd.date_range("2026-09-01", periods=bars, freq="h", tz="UTC")
    close = pd.Series(100.0, index=index)
    frame = pd.DataFrame(
        {"open": 100.0, "high": 100.1, "low": 99.9, "close": close, "volume": 1000.0}, index=index
    )
    return frame


def _midpoint(indicator: str) -> dict[str, Any]:
    space = PARAMETER_SPACE.get(indicator, {})
    return {key: values[len(values) // 2] for key, values in space.items()}


def _bar(frame: pd.DataFrame, i: int) -> Bar:
    row = frame.iloc[i]
    return Bar(
        timestamp=frame.index[i],
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )


@cache
def _prefix_signals(indicator: str, seed: int) -> tuple[tuple[bool, bool], ...]:
    """What the host sees bar by bar: each signal comes from the closed bars up to that row."""
    frame = _walk(BARS, seed)
    params = _midpoint(indicator)
    return tuple(
        last_closed_signals(indicator, frame.iloc[: i + 1], params, lookback_bars=MIN_LOOKBACK_BARS)
        for i in range(BARS)
    )


def _port_run(indicator: str, seed: int, cfg: BacktestConfig) -> tuple[list[Trade], PortState]:
    frame = _walk(BARS, seed)
    signals = _prefix_signals(indicator, seed)
    trader = StreamingTrader(cfg, warmup_bars=1, test_only_bar0_entry=True)
    trades: list[Trade] = []
    for i in range(BARS):
        buy, sell = signals[i]
        trades.extend(trader.on_closed_bar(i, _bar(frame, i), buy=buy, sell=sell))
    trades.extend(trader.flatten(_bar(frame, BARS - 1), BARS - 1))
    return trades, trader.state


def _engine_run(indicator: str, seed: int, cfg: BacktestConfig) -> tuple[list[Trade], float]:
    frame = _walk(BARS, seed)
    buy, sell = generate_indicator_signals(indicator, frame, _midpoint(indicator))
    result = run_backtest(frame, buy, sell, cfg)
    return result.trades, result.final_equity


@pytest.mark.parametrize("indicator", INDICATORS)
@pytest.mark.parametrize("config_name", sorted(CONFIGS))
def test_port_matches_engine_bar_for_bar(indicator: str, config_name: str) -> None:
    cfg = CONFIGS[config_name]
    engine_trades, engine_equity = _engine_run(indicator, 3, cfg)
    port_trades, state = _port_run(indicator, 3, cfg)
    assert [repr(t) for t in port_trades] == [repr(t) for t in engine_trades]
    assert repr(state.cash) == repr(engine_equity)


def test_the_parity_matrix_exercises_real_exits() -> None:
    reasons: set[str] = set()
    total = 0
    for indicator in INDICATORS:
        for cfg in CONFIGS.values():
            trades, _ = _port_run(indicator, 3, cfg)
            total += len(trades)
            reasons.update(t.exit_reason for t in trades)
    assert total >= 20
    assert {"sell_signal", "trailing_stop_loss", "end_of_data"} <= reasons


def test_restart_mid_run_matches_an_uninterrupted_run() -> None:
    frame = _walk(BARS, 5)
    signals = _prefix_signals("RSI", 5)
    cfg = BacktestConfig(trailing_stop_loss_pct=4.0)

    def run(restart_at: int | None) -> tuple[list[str], dict[str, Any]]:
        trader = StreamingTrader(cfg, warmup_bars=20)
        out: list[Trade] = []
        for i in range(BARS):
            if i == restart_at:
                saved = json.dumps(trader.state.to_dict())
                trader = StreamingTrader(
                    cfg, warmup_bars=20, state=PortState.from_dict(json.loads(saved))
                )
            buy, sell = signals[i]
            out.extend(trader.on_closed_bar(i, _bar(frame, i), buy=buy, sell=sell))
        out.extend(trader.flatten(_bar(frame, BARS - 1), BARS - 1))
        return [repr(t) for t in out], trader.state.to_dict()

    straight = run(None)
    assert straight[0], "the run must close at least one trade to mean anything"
    for restart_at in (1, 57, 133):
        assert run(restart_at) == straight


def test_a_replayed_bar_after_restart_changes_nothing() -> None:
    frame = _walk(5, 1)
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1)
    for i in range(5):
        trader.on_closed_bar(i, _bar(frame, i), buy=(i == 2), sell=False)
    before = trader.state.to_dict()
    assert trader.on_closed_bar(3, _bar(frame, 3), buy=True, sell=False) == []
    assert trader.state.to_dict() == before


def test_an_out_of_order_bar_is_refused() -> None:
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1)
    with pytest.raises(ValueError, match="out of order"):
        trader.on_closed_bar(4, _bar(_walk(5, 1), 4), buy=False, sell=False)


def test_no_entry_until_the_warm_up_history_is_full() -> None:
    frame = _walk(20, 2)
    trader = StreamingTrader(BacktestConfig(), warmup_bars=10)
    entered: list[int] = []
    for i in range(12):
        was_flat = trader.state.position_qty == 0
        trader.on_closed_bar(i, _bar(frame, i), buy=(i in (3, 11)), sell=False)
        if was_flat and trader.state.position_qty > 0:
            entered.append(i)
        if i == 3:
            assert trader.warmup_progress == pytest.approx(0.4)
    assert entered == [11]


def test_a_rising_edge_enters_once_and_a_held_signal_does_not_reenter() -> None:
    frame = _flat(12)
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1)
    opened: list[int] = []
    for i in range(12):
        was_flat = trader.state.position_qty == 0
        trader.on_closed_bar(i, _bar(frame, i), buy=(i in (2, 3, 4)), sell=False)
        if was_flat and trader.state.position_qty > 0:
            opened.append(i)
    assert opened == [2]


def test_a_bar_that_exits_cannot_also_enter() -> None:
    frame = _flat(3)
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1, test_only_bar0_entry=True)
    trader.on_closed_bar(0, _bar(frame, 0), buy=False, sell=False)
    closed = trader.on_closed_bar(1, _bar(frame, 1), buy=True, sell=True)
    assert [t.exit_reason for t in closed] == ["sell_signal"]
    assert trader.state.position_qty == 0
    assert trader.state.exited_on_bar == 1
    assert trader.on_closed_bar(2, _bar(frame, 2), buy=True, sell=False) == []
    assert trader.state.position_qty == 0


def test_live_starts_flat_without_the_test_flag() -> None:
    frame = _flat(3)
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1)
    trader.on_closed_bar(0, _bar(frame, 0), buy=False, sell=False)
    assert trader.state.position_qty == 0


def test_the_forming_bar_is_never_decided_on() -> None:
    frame = _walk(6, 8)
    interval = pd.Timedelta("1h")
    closed = drop_forming_bar(frame, interval=interval, now=frame.index[-1] + pd.Timedelta("30min"))
    assert len(closed) == 5
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1)
    for i in range(len(closed)):
        trader.on_closed_bar(i, _bar(closed, i), buy=False, sell=False)
    assert trader.state.bars_seen == 5
    whole = drop_forming_bar(frame, interval=interval, now=frame.index[-1] + interval)
    assert len(whole) == 6


def test_lookback_below_the_minimum_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 500"):
        last_closed_signals("RSI", _walk(50, 1), {}, lookback_bars=499)
