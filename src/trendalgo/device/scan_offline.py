"""Offline scan helpers for tests and `--selftest`: a fixed pair list and a synthetic market, so a scan
makes no Kraken call. The window and the app never import this module."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import patch

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner import listings, pipeline
from trendalgo.scanner.live_market import LiveMarketRow

OFFLINE_PAIRS: tuple[str, ...] = ("BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "DOT/USD")
BAR_SECONDS = 300
BARS = 25


def offline_market(pairs: list[str]) -> list[LiveMarketRow]:
    """A steadily rising synthetic market for each pair, with volume and gain above the default gates."""
    rows: list[LiveMarketRow] = []
    for index, pair in enumerate(pairs):
        gain = 0.04 + 0.005 * index
        rows.append(
            LiveMarketRow(pair=pair, bars=_trend_bars(gain), gain_pct=gain, volume_usd=1_000_000.0)
        )
    return rows


def _trend_bars(gain_pct: float, base: float = 100.0) -> list[OhlcvPoint]:
    start = int(datetime.now(UTC).timestamp()) - BARS * BAR_SECONDS
    price = base
    bars: list[OhlcvPoint] = []
    for index in range(BARS):
        price *= 1 + gain_pct / 20
        bars.append(
            OhlcvPoint(
                time=start + index * BAR_SECONDS,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1000.0,
            )
        )
    return bars


@contextmanager
def offline_listings(pairs: tuple[str, ...] = OFFLINE_PAIRS) -> Iterator[None]:
    """Use a fixed pair list while the block runs, so no Kraken call is made."""
    with (
        patch.object(listings, "verify_kraken_listings", return_value=list(pairs)),
        patch.object(pipeline, "verify_kraken_listings", return_value=list(pairs)),
    ):
        yield
