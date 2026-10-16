"""Backtest form logic: validate a request and format a result. Pure, so the page stays thin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trendalgo.device.fields import LIVE_V1_INDICATORS, TIMEFRAMES, check_pair, check_trailing_stop


@dataclass(frozen=True)
class BacktestRequest:
    pair: str
    timeframe: str
    indicator: str
    trailing_stop_pct: float


def validate_request(
    *,
    pair: str,
    timeframe: str,
    indicator: str,
    trailing_stop: str,
) -> tuple[BacktestRequest | None, list[str]]:
    errors: list[str] = []
    symbol = check_pair(pair)
    if symbol is None:
        errors.append("Pair: use BASE/QUOTE, for example BTC/USD.")
    if timeframe not in TIMEFRAMES:
        errors.append(f"Timeframe: choose {' or '.join(TIMEFRAMES)}.")
    if indicator not in LIVE_V1_INDICATORS:
        errors.append("Indicator: choose one of the live indicators.")
    stop = check_trailing_stop(trailing_stop)
    if stop is None:
        errors.append("Trailing stop: enter 0 to turn it off, or a percent from 1 to 20.")
    if errors or symbol is None or stop is None:
        return None, errors
    return BacktestRequest(symbol, timeframe, indicator, stop), []


def summary_rows(result: dict[str, Any]) -> list[tuple[str, str]]:
    """Labels and display values for the result panel."""
    return [
        ("Final equity", f"${float(result['final_equity']):,.2f}"),
        ("Net return", f"{float(result['net_pct']):+.2f}%"),
        ("Trades", str(int(result["total_trades"]))),
        ("Win rate", f"{float(result['win_pct']):.1f}%"),
    ]


def missing_candles_text(pair: str, timeframe: str) -> str:
    """Empty-state text. It says plainly that this app reads candles and does not download them."""
    return (
        f"No {timeframe} candles for {pair} in the data folder yet. This app reads saved candles "
        "only. It does not download them."
    )
