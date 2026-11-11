"""RISK-09: place reduce-only stop; restart adopts without duplicating."""

from __future__ import annotations

from typing import Any

from trendalgo.trading.exchange_stops import (
    StopBook,
    adopt_exchange_stops,
    place_reduce_only_stop,
)


class StubVenue:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.open: list[dict[str, Any]] = []

    def create_stop(
        self, pair: str, side: str, amount: float, stop_price: float, *, reduce_only: bool
    ) -> dict[str, Any]:
        assert reduce_only is True
        order = {
            "id": f"stop-{len(self.created) + 1}",
            "pair": pair,
            "side": side,
            "amount": amount,
            "stop_price": stop_price,
        }
        self.created.append(order)
        self.open.append(dict(order))
        return order

    def fetch_open_stops(self, pair: str | None = None) -> list[dict[str, Any]]:
        if pair is None:
            return list(self.open)
        return [row for row in self.open if row["pair"] == pair]


def test_process_kill_leaves_resting_stop_and_restart_adopts() -> None:
    venue = StubVenue()
    live_book = StopBook()
    placed = place_reduce_only_stop(
        venue,
        pair="BTC/USD",
        side="sell",
        amount=0.01,
        stop_price=40_000.0,
        book=live_book,
    )
    assert placed.exchange_order_id in live_book.by_id
    assert venue.open  # survives "process kill" on the venue

    # Fresh process: empty local book, venue still has the stop.
    restarted = StopBook()
    adopted = adopt_exchange_stops(venue, pair="BTC/USD", book=restarted)
    assert len(adopted) == 1
    assert adopted[0].exchange_order_id == placed.exchange_order_id

    # Second adopt must not duplicate.
    again = adopt_exchange_stops(venue, pair="BTC/USD", book=restarted)
    assert again == []
    assert len(restarted.by_id) == 1
