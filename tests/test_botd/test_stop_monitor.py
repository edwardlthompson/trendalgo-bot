"""p2-stop-monitor: 1-minute stops for open positions. The exit bar matches the engine (L1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.botd.lts_port.bar import Bar
from trendalgo.botd.lts_port.stop_monitor import StopMonitor
from trendalgo.botd.lts_port.trader import StreamingTrader
from trendalgo.lts_vendor.backtesting.engine import run_backtest
from trendalgo.lts_vendor.backtesting.models import BacktestConfig, Trade

HOUR0 = pd.Timestamp("2026-09-01 00:00:00", tz="UTC")
HOURS = 96
SEEDS = (0, 1, 2)
TSL_PCTS = (1.0, 3.0)
TP_PCTS = (0.0, 1.0, 2.0)  # 0.0 means take profit off
MINUTE_VOL = 0.002  # about 1.5% per hour: intrabar 1% stops really happen


class _Feed:
    """Stands in for the REST call. Counts calls and returns one forming minute."""

    def __init__(self, bar: Bar | None = None) -> None:
        self.calls = 0
        self.bar = bar

    def __call__(self) -> Bar | None:
        self.calls += 1
        return self.bar


def _open_trader(config: BacktestConfig | None = None) -> StreamingTrader:
    trader = StreamingTrader(config or BacktestConfig(), warmup_bars=1, test_only_bar0_entry=True)
    trader.on_closed_bar(0, Bar(HOUR0, high=100.0, low=100.0, close=100.0), buy=False, sell=False)
    return trader


def test_flat_means_no_rest_call() -> None:
    trader = StreamingTrader(BacktestConfig(), warmup_bars=1)
    feed = _Feed(Bar(HOUR0, high=100.0, low=100.0, close=100.0))
    assert StopMonitor(trader).poll(feed, HOUR0) is None
    assert feed.calls == 0


def test_polls_follow_the_interval_while_a_position_is_open() -> None:
    feed = _Feed(Bar(HOUR0, high=100.0, low=100.0, close=100.0))
    monitor = StopMonitor(_open_trader(), interval_s=30)
    monitor.poll(feed, HOUR0)
    monitor.poll(feed, HOUR0 + pd.Timedelta(seconds=10))
    monitor.poll(feed, HOUR0 + pd.Timedelta(seconds=30))
    assert feed.calls == 2


@pytest.mark.parametrize("interval_s", [5, 60])
def test_intervals_outside_15_to_30_seconds_are_refused(interval_s: int) -> None:
    with pytest.raises(ValueError, match="between 15 and 30"):
        StopMonitor(_open_trader(), interval_s=interval_s)


def test_a_stop_inside_the_forming_minute_exits_at_the_stop_price() -> None:
    trader = _open_trader()
    minute = HOUR0 + pd.Timedelta(hours=1, minutes=5)
    trade = trader.on_intrabar(Bar(minute, high=100.1, low=99.0, close=99.5))
    assert trade is not None
    assert trade.exit_reason == "trailing_stop_loss"
    assert trade.exit_price == pytest.approx(100.1 * 0.99)
    assert trade.exit_time == str(minute)
    assert trader.state.position_qty == 0
    assert trader.state.exited_on_bar == 1


def test_the_closed_bar_after_an_intrabar_exit_cannot_re_enter() -> None:
    trader = _open_trader()
    trader.on_intrabar(Bar(HOUR0 + pd.Timedelta(hours=1), high=100.1, low=99.0, close=99.5))
    closed = trader.on_closed_bar(
        1,
        Bar(HOUR0 + pd.Timedelta(hours=1), high=100.1, low=98.0, close=98.5),
        buy=True,
        sell=False,
    )
    assert closed == []
    assert trader.state.position_qty == 0


def _minutes(seed: int, vol: float) -> pd.DataFrame:
    n = HOURS * 60
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, vol, n)))
    high = close * (1.0 + np.abs(rng.normal(0.0, vol / 2.0, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, vol / 2.0, n)))
    open_ = np.concatenate(([close[0]], close[:-1]))
    index = pd.date_range("2026-09-01", periods=n, freq="min", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1.0}, index=index
    )


def _hourly(minutes: pd.DataFrame) -> pd.DataFrame:
    return minutes.resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )


def _bar_at(frame: pd.DataFrame, i: int) -> Bar:
    row = frame.iloc[i]
    return Bar(
        timestamp=frame.index[i],
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )


def _buy_flags(hours: int) -> list[bool]:
    return [h > 0 and h % 40 == 0 for h in range(hours)]


def _engine_trades(hourly: pd.DataFrame, cfg: BacktestConfig, buy: list[bool]) -> list[Trade]:
    buy_series = pd.Series(buy, index=hourly.index)
    sell_series = pd.Series(False, index=hourly.index)
    return run_backtest(hourly, buy_series, sell_series, cfg).trades


def _monitored_trades(
    minutes: pd.DataFrame, hourly: pd.DataFrame, cfg: BacktestConfig, buy: list[bool]
) -> tuple[list[Trade], int]:
    """Minute ticks drive the monitor. Each hour closes through the closed-bar path."""
    trader = StreamingTrader(cfg, warmup_bars=1, test_only_bar0_entry=True)
    monitor = StopMonitor(trader, interval_s=30)
    trades: list[Trade] = []
    intrabar = 0
    for h in range(len(hourly)):
        for m in range(h * 60, h * 60 + 60):
            tick = _bar_at(minutes, m)
            hit = monitor.poll(_Feed(tick), tick.timestamp)
            if hit is not None:
                trades.append(hit)
                intrabar += 1
        trades.extend(trader.on_closed_bar(h, _bar_at(hourly, h), buy=buy[h], sell=False))
    last = len(hourly) - 1
    trades.extend(trader.flatten(_bar_at(hourly, last), last))
    return trades, intrabar


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("tsl", TSL_PCTS)
@pytest.mark.parametrize("tp", TP_PCTS)
def test_the_exit_bar_matches_the_engine_and_the_fill_sits_inside_it(
    seed: int, tsl: float, tp: float
) -> None:
    minutes = _minutes(seed, MINUTE_VOL)
    hourly = _hourly(minutes)
    buy = _buy_flags(len(hourly))
    cfg = BacktestConfig(take_profit_pct=tp, trailing_stop_loss_pct=tsl)
    engine = _engine_trades(hourly, cfg, buy)
    monitored, _ = _monitored_trades(minutes, hourly, cfg, buy)
    assert len(monitored) == len(engine)
    for mon, eng in zip(monitored, engine, strict=True):
        hour = pd.Timestamp(eng.exit_time)
        assert pd.Timestamp(mon.exit_time).floor("h") == hour
        assert mon.exit_reason == eng.exit_reason
        assert mon.entry_time == eng.entry_time
        assert repr(mon.entry_price) == repr(eng.entry_price)
        # The fill may differ from the engine's (the monitor sees the minute path), but it must
        # lie inside the exit bar, so the gap is bounded by the bar's own range.
        bar = hourly.loc[hour]
        assert bar["low"] <= mon.exit_price <= bar["high"]
        assert bar["low"] <= eng.exit_price <= bar["high"]


def test_intrabar_stops_actually_happen_across_the_matrix() -> None:
    total = 0
    for seed in SEEDS:
        for tsl in TSL_PCTS:
            for tp in TP_PCTS:
                minutes = _minutes(seed, MINUTE_VOL)
                hourly = _hourly(minutes)
                cfg = BacktestConfig(take_profit_pct=tp, trailing_stop_loss_pct=tsl)
                _, intrabar = _monitored_trades(minutes, hourly, cfg, _buy_flags(len(hourly)))
                total += intrabar
    assert total >= 3
