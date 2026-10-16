"""E3: reconcile pending and unknown orders, halt on orphans, and gate new buys."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.trading.order_journal import (
    OrderHaltedError,
    OrderJournal,
    OrderOutcomeUnknownError,
    new_client_id,
)
from trendalgo.trading.reconcile import ensure_clear_for_buy, reconcile_exchange


class FakeClient:
    """Stands in for a ccxt client. Holds the open and closed orders the exchange reports."""

    def __init__(self) -> None:
        self.open_orders: list[dict[str, Any]] = []
        self.closed_orders: list[dict[str, Any]] = []
        self.since_seen: list[int | None] = []

    def fetch_open_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        self.since_seen.append(since)
        return list(self.open_orders)

    def fetch_closed_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        self.since_seen.append(since)
        return list(self.closed_orders)

    def fetch_order(self, order_id: str, symbol: str | None = None) -> dict[str, Any]:
        for order in self.open_orders + self.closed_orders:
            if str(order.get("id")) == order_id:
                return {"id": order_id, "filled": order.get("filled", 0.0)}
        return {"id": order_id, "filled": 0.0}

    def fetch_balance(self) -> dict[str, Any]:
        return {"total": {}}


class BrokenClient(FakeClient):
    def fetch_open_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        raise ConnectionError("exchange unreachable")


@pytest.fixture
def journal(tmp_path: Path) -> OrderJournal:
    return OrderJournal(tmp_path / "journal.db")


def _intent(journal: OrderJournal, status: str = "pending") -> str:
    client_id = new_client_id()
    journal.record_intent(client_id, "kraken", "BTC/USD", "buy", 0.0005)
    if status != "pending":
        journal.set_status(client_id, status)
    return client_id


def test_pending_order_found_on_exchange_is_settled(journal: OrderJournal) -> None:
    client = FakeClient()
    client_id = _intent(journal)
    client.closed_orders.append({"id": "O-9", "clientOrderId": client_id, "filled": 0.0005})
    report = reconcile_exchange(journal, client, "kraken")
    row = journal.get(client_id)
    assert report.settled == [client_id]
    assert row is not None
    assert row["status"] == "filled"  # settled, then its executed quantity is final
    assert row["exchange_order_id"] == "O-9"
    assert row["filled"] == pytest.approx(0.0005)


def test_unknown_order_not_on_exchange_stays_unresolved(journal: OrderJournal) -> None:
    client = FakeClient()
    client_id = _intent(journal, "unknown")
    report = reconcile_exchange(journal, client, "kraken")
    row = journal.get(client_id)
    assert report.unresolved == [client_id]
    assert row is not None
    assert row["status"] == "unknown"


def test_lookup_reaches_back_to_the_order_creation_time(journal: OrderJournal) -> None:
    client = FakeClient()
    client_id = _intent(journal)
    row = journal.get(client_id)
    assert row is not None
    reconcile_exchange(journal, client, "kraken")
    created_ms = float(row["created_at"]) * 1000
    lookups = [since for since in client.since_seen if since is not None]
    assert len(lookups) == 2  # open orders, then closed orders
    assert all(since <= created_ms for since in lookups)


def test_orphan_order_halts_the_exchange(journal: OrderJournal) -> None:
    client = FakeClient()
    orphan = "ta" + "a" * 16
    client.open_orders.append({"id": "O-7", "clientOrderId": orphan})
    report = reconcile_exchange(journal, client, "kraken")
    assert report.orphans == [orphan]
    assert journal.is_halted("kraken")
    assert not journal.is_halted("gemini")


def test_orders_without_our_prefix_are_not_orphans(journal: OrderJournal) -> None:
    client = FakeClient()
    client.open_orders.append({"id": "O-3", "clientOrderId": "manual-1"})
    client.open_orders.append({"id": "O-4"})
    report = reconcile_exchange(journal, client, "kraken")
    assert report.orphans == []
    assert not journal.is_halted("kraken")


def test_our_own_open_order_is_not_an_orphan(journal: OrderJournal) -> None:
    client = FakeClient()
    client_id = _intent(journal)
    journal.set_status(client_id, "submitted", exchange_order_id="O-5")
    client.open_orders.append({"id": "O-5", "clientOrderId": client_id})
    assert reconcile_exchange(journal, client, "kraken").orphans == []


def test_buy_waits_while_an_earlier_order_is_unresolved(journal: OrderJournal) -> None:
    _intent(journal, "unknown")
    with pytest.raises(OrderOutcomeUnknownError, match="unresolved"):
        ensure_clear_for_buy(journal, FakeClient(), "kraken")


def test_buy_proceeds_once_earlier_orders_are_settled(journal: OrderJournal) -> None:
    client = FakeClient()
    client_id = _intent(journal)
    client.closed_orders.append({"id": "O-9", "clientOrderId": client_id, "filled": 0.0005})
    ensure_clear_for_buy(journal, client, "kraken")  # no exception
    row = journal.get(client_id)
    assert row is not None
    assert row["status"] == "filled"


def test_buy_is_refused_when_an_orphan_exists(journal: OrderJournal) -> None:
    client = FakeClient()
    client.open_orders.append({"id": "O-7", "clientOrderId": "ta" + "b" * 16})
    with pytest.raises(OrderHaltedError, match="orphan"):
        ensure_clear_for_buy(journal, client, "kraken")


def test_buy_is_refused_while_the_exchange_is_halted(journal: OrderJournal) -> None:
    journal.halt("kraken", "orphan order on the exchange")
    with pytest.raises(OrderHaltedError, match="halted"):
        ensure_clear_for_buy(journal, FakeClient(), "kraken")


def test_buy_is_refused_when_reconciliation_fails(journal: OrderJournal) -> None:
    with pytest.raises(OrderOutcomeUnknownError, match="reconciliation failed"):
        ensure_clear_for_buy(journal, BrokenClient(), "kraken")
