"""Exchange-side reduce-only stops (RISK-09).

Local stops die with the process. On entry, place a real reduce-only stop at the venue and
adopt any resting stop on restart instead of duplicating. Full ccxt wiring lands with LIVE
work; these stubs define the place/adopt contract for tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class StopVenue(Protocol):
    def create_stop(
        self, pair: str, side: str, amount: float, stop_price: float, *, reduce_only: bool
    ) -> dict[str, Any]: ...

    def fetch_open_stops(self, pair: str | None = None) -> list[dict[str, Any]]: ...


@dataclass
class AdoptedStop:
    exchange_order_id: str
    pair: str
    side: str
    amount: float
    stop_price: float


@dataclass
class StopBook:
    """In-process registry of stops we own, keyed by exchange order id."""

    by_id: dict[str, AdoptedStop] = field(default_factory=dict)


def place_reduce_only_stop(
    venue: StopVenue,
    *,
    pair: str,
    side: str,
    amount: float,
    stop_price: float,
    book: StopBook,
) -> AdoptedStop:
    """Place a reduce-only stop and record it locally."""
    raw = venue.create_stop(pair, side, amount, stop_price, reduce_only=True)
    order_id = str(raw.get("id") or "")
    if not order_id:
        raise ValueError("venue stop response missing id")
    stop = AdoptedStop(
        exchange_order_id=order_id,
        pair=pair,
        side=side,
        amount=amount,
        stop_price=stop_price,
    )
    book.by_id[order_id] = stop
    return stop


def adopt_exchange_stops(
    venue: StopVenue,
    *,
    pair: str | None,
    book: StopBook,
) -> list[AdoptedStop]:
    """On restart, adopt resting venue stops; never duplicate ids already in the book."""
    adopted: list[AdoptedStop] = []
    for raw in venue.fetch_open_stops(pair):
        order_id = str(raw.get("id") or "")
        if not order_id or order_id in book.by_id:
            continue
        stop = AdoptedStop(
            exchange_order_id=order_id,
            pair=str(raw.get("pair") or pair or ""),
            side=str(raw.get("side") or ""),
            amount=float(raw.get("amount") or 0.0),
            stop_price=float(raw.get("stop_price") or raw.get("stopPrice") or 0.0),
        )
        book.by_id[order_id] = stop
        adopted.append(stop)
    return adopted
