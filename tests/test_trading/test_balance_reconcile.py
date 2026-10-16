"""E3: exchange balances must match the journal, and a partial fill counts what filled."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.private_client import SerializedExchange
from trendalgo.exchanges.registry import get_entry
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.trading.order_journal import (
    OrderHaltedError,
    OrderJournal,
    OrderOutcomeUnknownError,
    new_client_id,
)
from trendalgo.trading.order_journal_store import default_journal
from trendalgo.trading.reconcile import accept_balance, ensure_clear_for_buy, reconcile_exchange

WATCH_BTC = ("BTC",)


class FakeAccount:
    """A ccxt-like account on one BTC/USD market. Balances move only when an order fills."""

    def __init__(self) -> None:
        self.total: dict[str, float] = {}
        self.orders: dict[str, dict[str, Any]] = {}
        self.fetch_order_error: Exception | None = None

    def nonce(self) -> int:
        return 1_700_000_000_000

    def fill(self, order_id: str, quantity: float) -> None:
        """Execute more of one order. Its executed quantity and the BTC balance move together."""
        order = self.orders[order_id]
        order["filled"] += quantity
        signed = quantity if order["side"] == "buy" else -quantity
        self.total["BTC"] = self.total.get("BTC", 0.0) + signed

    def close(self, order_id: str) -> None:
        self.orders[order_id]["status"] = "closed"

    def fetch_balance(self) -> dict[str, Any]:
        return {"total": dict(self.total)}

    def fetch_tickers(self) -> dict[str, Any]:
        return {}

    def fetch_open_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        return [dict(o) for o in self.orders.values() if o["status"] == "open"]

    def fetch_closed_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        return [dict(o) for o in self.orders.values() if o["status"] != "open"]

    def fetch_order(self, order_id: str, symbol: str | None = None) -> dict[str, Any]:
        if self.fetch_order_error is not None:
            raise self.fetch_order_error
        return dict(self.orders[order_id])


def _place(journal: OrderJournal, account: FakeAccount, side: str, amount: float) -> str:
    """Journal an order the way the adapter does, and open it on the account. Returns its id."""
    client_id = new_client_id()
    order_id = f"O-{len(account.orders) + 1}"
    journal.record_intent(client_id, "kraken", "BTC/USD", side, amount)
    journal.set_status(client_id, "submitted", exchange_order_id=order_id)
    account.orders[order_id] = {
        "id": order_id,
        "clientOrderId": client_id,
        "side": side,
        "filled": 0.0,
        "status": "open",
    }
    return order_id


@pytest.fixture
def journal(tmp_path: Path) -> OrderJournal:
    return OrderJournal(tmp_path / "journal.db")


@pytest.fixture
def account() -> FakeAccount:
    return FakeAccount()


def test_first_check_takes_a_baseline_and_a_fill_is_explained(
    journal: OrderJournal, account: FakeAccount
) -> None:
    account.total["BTC"] = 2.0  # held before the bot traded: this is the baseline
    assert reconcile_exchange(journal, account, "kraken", WATCH_BTC).mismatches == []
    order_id = _place(journal, account, "buy", 0.5)
    account.fill(order_id, 0.5)
    account.close(order_id)
    report = reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    assert report.mismatches == []
    assert not journal.is_halted("kraken")
    assert journal.rows("kraken")[0]["status"] == "filled"


def test_buy_path_takes_the_baseline_before_the_first_order(
    journal: OrderJournal, account: FakeAccount
) -> None:
    account.total["BTC"] = 1.0
    ensure_clear_for_buy(journal, account, "kraken", "BTC/USD")  # first sight: the baseline
    account.total["BTC"] = 1.2  # the owner buys by hand on the same key
    with pytest.raises(OrderHaltedError, match="unexplained balance change"):
        ensure_clear_for_buy(journal, account, "kraken", "BTC/USD")
    assert journal.is_halted("kraken")


def test_an_unexplained_balance_halts_the_exchange(
    journal: OrderJournal, account: FakeAccount
) -> None:
    account.total["BTC"] = 1.0
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    account.total["BTC"] = 1.5  # a deposit or a manual trade: no order of ours explains it
    report = reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    assert [m.asset for m in report.mismatches] == ["BTC"]
    assert report.halt_reason is not None
    assert "BTC" in report.halt_reason
    assert journal.is_halted("kraken")
    with pytest.raises(OrderHaltedError, match="halted"):
        ensure_clear_for_buy(journal, account, "kraken", "BTC/USD")


def test_a_manual_trade_after_a_bot_fill_is_unexplained(
    journal: OrderJournal, account: FakeAccount
) -> None:
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    order_id = _place(journal, account, "buy", 0.5)
    account.fill(order_id, 0.5)
    account.close(order_id)
    account.total["BTC"] += 0.3  # the owner trades on the same key
    assert reconcile_exchange(journal, account, "kraken", WATCH_BTC).mismatches
    assert journal.is_halted("kraken")


def test_a_partial_fill_counts_what_filled_not_what_was_requested(
    journal: OrderJournal, account: FakeAccount
) -> None:
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    order_id = _place(journal, account, "buy", 1.0)
    account.fill(order_id, 0.4)  # still open with 0.6 to go
    report = reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    assert report.open
    assert report.mismatches == []  # an open order defers the balance check
    assert not journal.is_halted("kraken")
    row = journal.rows("kraken")[0]
    assert row["status"] == "submitted"
    assert row["filled"] == pytest.approx(0.4)
    with pytest.raises(OrderOutcomeUnknownError, match="still open"):
        ensure_clear_for_buy(journal, account, "kraken", "BTC/USD")
    account.close(order_id)  # the exchange cancels the unfilled 0.6
    report = reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    row = journal.rows("kraken")[0]
    assert row["status"] == "closed"
    assert row["filled"] == pytest.approx(0.4)
    assert report.mismatches == []
    assert not journal.is_halted("kraken")


def test_a_partial_fill_that_completes_is_final(
    journal: OrderJournal, account: FakeAccount
) -> None:
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    order_id = _place(journal, account, "buy", 1.0)
    account.fill(order_id, 0.4)
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    account.fill(order_id, 0.6)
    account.close(order_id)
    report = reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    row = journal.rows("kraken")[0]
    assert row["status"] == "filled"
    assert row["filled"] == pytest.approx(1.0)
    assert report.mismatches == []
    assert not journal.is_halted("kraken")


def test_a_sell_lowers_the_expected_position(journal: OrderJournal, account: FakeAccount) -> None:
    account.total["BTC"] = 1.0
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    order_id = _place(journal, account, "sell", 0.25)
    account.fill(order_id, 0.25)
    account.close(order_id)
    report = reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    assert report.mismatches == []
    assert not journal.is_halted("kraken")
    assert account.total["BTC"] == pytest.approx(0.75)


def test_a_failed_fill_read_refuses_the_buy_without_halting(
    journal: OrderJournal, account: FakeAccount
) -> None:
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    order_id = _place(journal, account, "buy", 0.5)
    account.fill(order_id, 0.5)
    account.close(order_id)
    account.fetch_order_error = ConnectionError("exchange unreachable")
    with pytest.raises(OrderOutcomeUnknownError, match="reconciliation failed"):
        ensure_clear_for_buy(journal, account, "kraken", "BTC/USD")
    assert not journal.is_halted("kraken")


def test_operator_accepts_a_balance_then_buys_resume(
    journal: OrderJournal, account: FakeAccount
) -> None:
    account.total["BTC"] = 1.0
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    account.total["BTC"] = 1.5  # a deposit
    reconcile_exchange(journal, account, "kraken", WATCH_BTC)
    assert journal.is_halted("kraken")
    assert accept_balance(journal, account, "kraken", "BTC") == pytest.approx(1.5)
    journal.reset_halt("kraken")
    ensure_clear_for_buy(journal, account, "kraken", "BTC/USD")  # no exception
    assert not journal.is_halted("kraken")


def test_accept_refuses_while_an_order_is_still_open(
    journal: OrderJournal, account: FakeAccount
) -> None:
    order_id = _place(journal, account, "buy", 1.0)
    account.fill(order_id, 0.4)
    with pytest.raises(OrderOutcomeUnknownError, match="settle earlier orders"):
        accept_balance(journal, account, "kraken", "BTC")


def test_balance_sync_notifies_once_when_a_halt_is_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, account: FakeAccount
) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    wrapped = SerializedExchange(account)
    monkeypatch.setattr(GenericCcxtPortfolioAdapter, "_client", lambda self: wrapped)
    adapter = GenericCcxtPortfolioAdapter(get_entry("kraken"))
    store = PortfolioStore(tmp_path / "portfolio.db")
    journal = default_journal()
    order_id = _place(journal, account, "buy", 0.5)
    account.fill(order_id, 0.5)
    account.close(order_id)
    first = adapter.sync_balances(store, dry_run=False)
    assert first["reconcile"]["halted"] is None
    account.total["BTC"] += 0.4  # unexplained: no order of ours
    second = adapter.sync_balances(store, dry_run=False)
    assert "unexplained balance change" in second["reconcile"]["halted"]
    adapter.sync_balances(store, dry_run=False)  # still halted: no second notice
    notices = store.list_notifications()
    assert [notice["category"] for notice in notices] == ["trading"]


def test_a_halt_set_by_a_buy_is_announced_by_the_next_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, account: FakeAccount
) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    wrapped = SerializedExchange(account)
    monkeypatch.setattr(GenericCcxtPortfolioAdapter, "_client", lambda self: wrapped)
    adapter = GenericCcxtPortfolioAdapter(get_entry("kraken"))
    store = PortfolioStore(tmp_path / "portfolio.db")
    journal = default_journal()
    account.total["BTC"] = 1.0
    ensure_clear_for_buy(journal, wrapped, "kraken", "BTC/USD")  # the baseline, from a buy
    account.total["BTC"] = 1.4  # unexplained: no order of ours
    with pytest.raises(OrderHaltedError, match="unexplained balance change"):
        ensure_clear_for_buy(journal, wrapped, "kraken", "BTC/USD")  # the buy halts first
    adapter.sync_balances(store, dry_run=False)  # the sync still reports the halt
    notices = store.list_notifications()
    assert [notice["category"] for notice in notices] == ["trading"]
    assert "unexplained balance change" in str(notices[0]["body"])
