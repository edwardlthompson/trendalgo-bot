"""E2, E3, E8: client ids, lookup before retry, halts, reconciliation, and serialized calls."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any

import ccxt
import pytest

from trendalgo.exchanges.private_client import SerializedExchange
from trendalgo.exchanges.registry import get_entry
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.multi_exchange import route_order
from trendalgo.trading.order_guard import MAX_CONSECUTIVE_FAILURES
from trendalgo.trading.order_journal import OrderHaltedError, OrderOutcomeUnknownError
from trendalgo.trading.order_journal_store import default_journal
from trendalgo.trading.runner.adapters.generic import GenericCcxtTradingAdapter


class FakeExchange:
    """ccxt stand-in for kraken. Records calls and placed orders, and injects failures.

    A market order fills at once: the BTC balance moves by its full quantity.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.placed: list[dict[str, Any]] = []
        self.params: list[dict[str, Any]] = []
        self.total: dict[str, float] = {"BTC": 0.0}
        self.fail_before_placing: Exception | None = None
        self.fail_after_placing: Exception | None = None

    def nonce(self) -> int:
        return int(time.time() * 1000)

    def fetch_balance(self) -> dict[str, Any]:
        self.calls.append("fetch_balance")
        return {"total": dict(self.total)}

    def fetch_order(self, order_id: str, symbol: str | None = None) -> dict[str, Any]:
        self.calls.append("fetch_order")
        return next((dict(order) for order in self.placed if order["id"] == order_id), {})

    def fetch_ticker(self, pair: str) -> dict[str, Any]:
        return {"last": 50_000.0, "bid": None, "ask": None, "timestamp": time.time() * 1000}

    def load_markets(self) -> dict[str, Any]:
        return {}

    def market(self, pair: str) -> dict[str, Any]:
        return {"limits": {"amount": {"min": 0.0001}, "cost": {"min": 5.0}}}

    def amount_to_precision(self, pair: str, amount: float) -> str:
        return str(Decimal(repr(amount)).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN))

    def create_order(
        self,
        pair: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append("create_order")
        if self.fail_before_placing is not None:
            raise self.fail_before_placing
        client_id = (params or {}).get("clientOrderId")
        order_id = f"order-{len(self.placed) + 1}"
        self.placed.append({"id": order_id, "clientOrderId": client_id, "filled": amount})
        self.params.append(dict(params or {}))
        self.total["BTC"] += amount if side == "buy" else -amount
        if self.fail_after_placing is not None:
            raise self.fail_after_placing
        return {"id": order_id, "clientOrderId": client_id, "status": "open"}

    def fetch_open_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append("fetch_open_orders")
        return []

    def fetch_closed_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append("fetch_closed_orders")
        return list(self.placed)


class NonceExchange(FakeExchange):
    """Every call reads the same millisecond, the worst case for a nonce. Records overlap."""

    def __init__(self) -> None:
        super().__init__()
        self.clock_ms = 1_700_000_000_000
        self.nonces: list[int] = []
        self.in_flight = 0
        self.max_in_flight = 0

    def nonce(self) -> int:
        return self.clock_ms

    def create_order(
        self,
        pair: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.nonces.append(self.nonce())
        time.sleep(0.002)
        self.in_flight -= 1
        return super().create_order(pair, order_type, side, amount, price, params)


def _wire(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake: FakeExchange) -> None:
    entry = get_entry("kraken")
    monkeypatch.setenv(entry.env_key, "test-key")
    monkeypatch.setenv(entry.env_secret, "test-secret")
    monkeypatch.setenv("WORLDWIDE_TRADING_ACK", "1")
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    # H2: live orders need the owner's approval in the host store. GO_LIVE_APPROVED is not read.
    ExchangeControlStore(tmp_path / "exchange_control.db").approve_go_live("kraken")
    wrapped = SerializedExchange(fake)
    monkeypatch.setattr(GenericCcxtTradingAdapter, "_client", lambda self: wrapped)


@pytest.fixture
def kraken(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeExchange:
    fake = FakeExchange()
    _wire(monkeypatch, tmp_path, fake)
    return fake


def test_order_is_journaled_with_its_client_id(kraken: FakeExchange) -> None:
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert kraken.placed[0]["clientOrderId"] == result["client_id"]
    row = default_journal().get(result["client_id"])
    assert row is not None
    assert row["status"] == "submitted"
    assert row["exchange_order_id"] == "order-1"


def test_kraken_orders_take_fees_in_quote_currency(kraken: FakeExchange) -> None:
    route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    route_order("kraken", "BTC/USD", "sell", 25.0, dry_run=False)
    assert [params["oflags"] for params in kraken.params] == ["fciq", "fciq"]


def test_client_ids_differ_per_order(kraken: FakeExchange) -> None:
    first = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    second = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert first["client_id"] != second["client_id"]


def test_refused_order_is_not_looked_up_or_resent(kraken: FakeExchange) -> None:
    kraken.fail_before_placing = ccxt.InsufficientFunds("no funds")
    with pytest.raises(ccxt.InsufficientFunds):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    # Only the pre-buy reconciliation touched the exchange: no lookup and no second create.
    assert kraken.calls == ["fetch_open_orders", "fetch_balance", "create_order"]
    assert default_journal().count_by_status("rejected") == 1


def test_lost_reply_is_recovered_by_lookup(kraken: FakeExchange) -> None:
    kraken.fail_after_placing = ccxt.RequestTimeout("socket timed out")
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert kraken.calls == [
        "fetch_open_orders",
        "fetch_balance",
        "create_order",
        "fetch_open_orders",
        "fetch_closed_orders",
    ]
    assert len(kraken.placed) == 1
    assert result["order_id"] == "order-1"
    assert default_journal().count_by_status("submitted") == 1


def test_timeout_without_a_placed_order_is_unknown_and_not_resent(kraken: FakeExchange) -> None:
    kraken.fail_before_placing = ccxt.RequestTimeout("socket timed out")
    with pytest.raises(OrderOutcomeUnknownError):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert kraken.calls.count("create_order") == 1
    assert default_journal().count_by_status("unknown") == 1


def test_unresolved_order_blocks_the_next_buy_but_not_a_sell(kraken: FakeExchange) -> None:
    kraken.fail_before_placing = ccxt.RequestTimeout("socket timed out")
    with pytest.raises(OrderOutcomeUnknownError):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    kraken.fail_before_placing = None
    kraken.calls.clear()
    with pytest.raises(OrderOutcomeUnknownError, match="unresolved"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert "create_order" not in kraken.calls  # the second buy was never sent
    result = route_order("kraken", "BTC/USD", "sell", 25.0, dry_run=False)
    assert result["status"] == "open"  # exits still go through


def test_repeated_failures_halt_new_buys_but_not_exits(kraken: FakeExchange) -> None:
    kraken.fail_before_placing = ccxt.InsufficientFunds("no funds")
    for _ in range(MAX_CONSECUTIVE_FAILURES):
        with pytest.raises(ccxt.InsufficientFunds):
            route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert default_journal().count_by_status("rejected") == MAX_CONSECUTIVE_FAILURES

    kraken.calls.clear()
    with pytest.raises(OrderHaltedError):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert kraken.calls == []  # the halted buy never reached the exchange

    kraken.fail_before_placing = None
    result = route_order("kraken", "BTC/USD", "sell", 25.0, dry_run=False)
    assert result["status"] == "open"
    assert len(kraken.placed) == 1  # the exit went through


def test_concurrent_orders_never_overlap_or_repeat_a_nonce(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = NonceExchange()
    _wire(monkeypatch, tmp_path, fake)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda _: route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False),
                range(40),
            )
        )
    assert len(results) == 40
    assert fake.max_in_flight == 1  # calls on the key never overlapped
    assert len(set(fake.nonces)) == 40  # no nonce was reused
    assert fake.nonces == sorted(fake.nonces)
    # Each buy settles the one before it, so only the last order is still unfinished.
    assert default_journal().count_by_status("filled") == 39
    assert default_journal().count_by_status("submitted") == 1
    assert not default_journal().is_halted("kraken")
