"""Parity harness (p2-parity-harness; L5, L6): golden trade lists, window signals, TA-Lib digests.

Regenerate the fixtures only after an intentional, reviewed change:
    python -m tests.test_lts_vendor.parity_support
"""

from __future__ import annotations

import gzip
import json
import platform
import sys
from collections.abc import Mapping
from dataclasses import asdict
from functools import cache
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.botd.lts_port.bar import Bar
from trendalgo.botd.lts_port.closed_signals import MIN_LOOKBACK_BARS, last_closed_signals
from trendalgo.botd.lts_port.trader import StreamingTrader
from trendalgo.lts_vendor.backtesting.engine import run_backtest
from trendalgo.lts_vendor.backtesting.models import BacktestConfig, Trade
from trendalgo.lts_vendor.backtesting.parameter_space import PARAMETER_SPACE
from trendalgo.lts_vendor.backtesting.signals import generate_indicator_signals, talib_available

from .engine_golden_support import INDICATORS, SEEDS, _config, _midpoint, digest, make_frame

GOLDEN_BARS = 720
TALIB_INDICATORS = ("Stochastic", "CCI", "Ultimate Oscillator", "MFI", "ADX", "Parabolic SAR")
TRADE_FIXTURE = Path(__file__).parent / "fixtures" / "engine_golden_trades.json.gz"
TALIB_FIXTURE = Path(__file__).parent / "fixtures" / "talib_arch.json"
TRADE_CONFIGS: dict[str, BacktestConfig] = {
    "tsl2": _config(2.0),
    "tsl8": _config(8.0),
    "tsl20": _config(20.0),
    "tp3_tsl8": _config(8.0, 3.0),
}
CASES = [
    (indicator, seed, config_name)
    for indicator in INDICATORS
    for seed in SEEDS
    for config_name in TRADE_CONFIGS
]


def case_key(indicator: str, seed: int, config_name: str) -> str:
    return f"{indicator}/{seed}/{config_name}"


def trade_rows(trades: list[Trade]) -> list[dict[str, Any]]:
    """Exact, JSON-safe view of each trade: floats as repr, so no precision is lost."""
    return [
        {
            key: (repr(value) if isinstance(value, float) else value)
            for key, value in asdict(t).items()
        }
        for t in trades
    ]


def engine_trades(indicator: str, seed: int, config_name: str) -> list[Trade]:
    frame = make_frame(GOLDEN_BARS, seed)
    buy, sell = generate_indicator_signals(indicator, frame, _midpoint(indicator))
    return run_backtest(frame, buy, sell, TRADE_CONFIGS[config_name]).trades


@cache
def window_signals(indicator: str, seed: int) -> tuple[tuple[bool, bool], ...]:
    """What the host sees bar by bar: each signal comes from the last 500 closed bars (L5)."""
    frame = make_frame(GOLDEN_BARS, seed)
    params = _midpoint(indicator)
    return tuple(
        last_closed_signals(indicator, frame.iloc[: i + 1], params, lookback_bars=MIN_LOOKBACK_BARS)
        for i in range(GOLDEN_BARS)
    )


def window_flips(indicator: str, frame: pd.DataFrame, params: Mapping[str, Any]) -> list[int]:
    """Bars from the first full window on where the 500-bar signal differs from full history."""
    buy, sell = generate_indicator_signals(indicator, frame, dict(params))
    buy = buy.fillna(False).astype(bool)
    sell = sell.fillna(False).astype(bool)
    flips: list[int] = []
    for i in range(MIN_LOOKBACK_BARS - 1, len(frame)):
        window = last_closed_signals(
            indicator, frame.iloc[: i + 1], params, lookback_bars=MIN_LOOKBACK_BARS
        )
        if window != (bool(buy.iloc[i]), bool(sell.iloc[i])):
            flips.append(i)
    return flips


def grid_flip_report(seed: int = 0) -> dict[str, int]:
    """Flipped bars per indicator across its whole parameter grid. Slow (minutes): run by hand."""
    frame = make_frame(GOLDEN_BARS, seed)
    report: dict[str, int] = {}
    for indicator, space in PARAMETER_SPACE.items():
        if indicator in TALIB_INDICATORS and not talib_available():
            continue
        keys = list(space)
        report[indicator] = sum(
            len(window_flips(indicator, frame, dict(zip(keys, values, strict=True))))
            for values in product(*(space[key] for key in keys))
        )
    return report


def _bar(frame: pd.DataFrame, i: int) -> Bar:
    row = frame.iloc[i]
    return Bar(
        timestamp=frame.index[i],
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
    )


def port_trades(indicator: str, seed: int, config_name: str) -> list[Trade]:
    """The streaming port on closed bars with window signals. It must reproduce the golden lists."""
    frame = make_frame(GOLDEN_BARS, seed)
    signals = window_signals(indicator, seed)
    trader = StreamingTrader(TRADE_CONFIGS[config_name], warmup_bars=1, test_only_bar0_entry=True)
    trades: list[Trade] = []
    for i in range(GOLDEN_BARS):
        buy, sell = signals[i]
        trades.extend(trader.on_closed_bar(i, _bar(frame, i), buy=buy, sell=sell))
    trades.extend(trader.flatten(_bar(frame, GOLDEN_BARS - 1), GOLDEN_BARS - 1))
    return trades


def current_arch() -> str:
    machine = platform.machine().lower()
    return {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)


def talib_digests() -> dict[str, str]:
    """Full-history digests of the TA-Lib indicators on the golden frames (TSL 8, midpoint)."""
    out: dict[str, str] = {}
    for indicator in TALIB_INDICATORS:
        for seed in SEEDS:
            frame = make_frame(GOLDEN_BARS, seed)
            buy, sell = generate_indicator_signals(indicator, frame, _midpoint(indicator))
            result = run_backtest(frame, buy, sell, TRADE_CONFIGS["tsl8"])
            out[f"{indicator}/{seed}"] = digest(result)
    return out


def dump_trades(trades: dict[str, list[dict[str, Any]]]) -> str:
    """One trade per line, so a regenerated fixture diffs trade by trade."""
    blocks = [
        f"{json.dumps(key)}: [\n"
        + ",\n".join(json.dumps(row, sort_keys=True) for row in rows)
        + "\n]"
        for key, rows in sorted(trades.items())
    ]
    body = ",\n".join(blocks)
    return f'{{\n"bars": {GOLDEN_BARS},\n"trades": {{\n{body}\n}},\n"version": 1\n}}\n'


def write_trade_fixture() -> None:
    trades = {case_key(*case): trade_rows(engine_trades(*case)) for case in CASES}
    # Gzip keeps the fixture under the 500 KB tracked-file hygiene budget.
    TRADE_FIXTURE.write_bytes(gzip.compress(dump_trades(trades).encode("utf-8"), compresslevel=9))


def write_talib_capture() -> None:
    """Record this machine's TA-Lib digests under its own architecture. Other entries stay as they are."""
    if not talib_available():
        raise SystemExit("TA-Lib is required to capture its digests")
    data = json.loads(TALIB_FIXTURE.read_text(encoding="utf-8"))
    data["architectures"][current_arch()] = {"digests": talib_digests()}
    TALIB_FIXTURE.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--grid" in sys.argv:
        print(json.dumps(grid_flip_report(), indent=1, sort_keys=True))
    else:
        write_trade_fixture()
        if talib_available():
            write_talib_capture()
