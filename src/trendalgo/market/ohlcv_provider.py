"""Unified OHLCV provider: prefer registry exchange; fall back explicitly labeled."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from trendalgo.market.ccxt_ohlcv import fetch_exchange_ohlcv
from trendalgo.market.types import OhlcvPoint


class OhlcvProvider(Protocol):
    def fetch(
        self,
        exchange_id: str,
        pair: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[OhlcvPoint]: ...


class CcxtOhlcvProvider:
    """CCXT depth for any registry venue (Binance.US / Coinbase / Gemini / …)."""

    def fetch(
        self,
        exchange_id: str,
        pair: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[OhlcvPoint]:
        return fetch_exchange_ohlcv(exchange_id, pair, timeframe, since, until)


_DEFAULT = CcxtOhlcvProvider()


def default_ohlcv_provider() -> CcxtOhlcvProvider:
    return _DEFAULT


def fetch_ohlcv(
    exchange_id: str,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    provider: OhlcvProvider | None = None,
) -> list[OhlcvPoint]:
    """Fetch bars for ``exchange_id`` (not hard-wired to Kraken)."""
    eng = provider or _DEFAULT
    return eng.fetch(exchange_id, pair, timeframe, since, until)


# Priority venues for research-parity depth smoke (CEX-P3a).
PARITY_OHLCV_EXCHANGES: tuple[str, ...] = (
    "kraken",
    "binanceus",
    "coinbaseadvanced",
    "gemini",
)
