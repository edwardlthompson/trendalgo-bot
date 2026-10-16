"""Field rules shared by the plan builder and the backtest form. Pure, so both pages agree."""

from __future__ import annotations

import math
import re

LIVE_V1_INDICATORS: tuple[str, ...] = (
    "Bollinger %B",
    "EMA Crossover",
    "Heikin Ashi",
    "MACD",
    "RSI",
    "SMA Crossover",
)
TIMEFRAMES: tuple[str, ...] = tuple(f"{hour}h" for hour in range(1, 25))
TRAILING_STOP_MIN = 1.0
TRAILING_STOP_MAX = 20.0
_PAIR = re.compile(r"[A-Z0-9]{2,10}/[A-Z]{2,5}")


def parse_number(text: str) -> float | None:
    """A finite number from user text. Commas are allowed as thousands separators."""
    try:
        value = float(text.strip().replace(",", ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def check_pair(text: str) -> str | None:
    """The pair in BASE/QUOTE form, upper case. None when the text does not fit that form."""
    symbol = text.strip().upper()
    return symbol if _PAIR.fullmatch(symbol) else None


def check_trailing_stop(text: str) -> float | None:
    """0 turns the stop off. Otherwise a percent from 1 to 20. Anything else gives None."""
    value = parse_number(text)
    if value is None:
        return None
    if value == 0:
        return 0.0
    if TRAILING_STOP_MIN <= value <= TRAILING_STOP_MAX:
        return value
    return None
