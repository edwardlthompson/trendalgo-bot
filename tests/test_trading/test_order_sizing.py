"""E1: live orders are sized from a real ticker price, with freshness, precision and minimums."""

from __future__ import annotations

import time
from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any

import pytest

from trendalgo.exchanges.private_client import SerializedExchange
from trendalgo.exchanges.registry import get_entry
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.multi_exchange import route_order
from trendalgo.trading.runner.adapters.generic import GenericCcxtTradingAdapter


class FakeExchange:
    """ccxt stand-in with one BTC/USD market. Records every order it receives."""

    def __init__(self) -> None:
        self.last: float | None = 50_000.0
        self.bid: float | None = None
        self.ask: float | None = None
        self.timestamp: float | None = time.time() * 1000
        self.min_amount: float | None = 0.0001
        self.min_cost: float | None = 5.0
        self.ticker_error: Exception | None = None
        self.orders: list[tuple[str, str, str, float]] = []

    def nonce(self) -> int:
        return int(time.time() * 1000)

    def fetch_open_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        return []

    def fetch_closed_orders(
        self, pair: str | None = None, since: int | None = None
    ) -> list[dict[str, Any]]:
        return []

    def fetch_balance(self) -> dict[str, Any]:
        return {"total": {}}

    def fetch_ticker(self, pair: str) -> dict[str, Any]:
        if self.ticker_error is not None:
            raise self.ticker_error
        return {
            "last": self.last,
            "bid": self.bid,
            "ask": self.ask,
            "timestamp": self.timestamp,
        }

    def load_markets(self) -> dict[str, Any]:
        return {}

    def market(self, pair: str) -> dict[str, Any]:
        return {"limits": {"amount": {"min": self.min_amount}, "cost": {"min": self.min_cost}}}

    def amount_to_precision(self, pair: str, amount: float) -> str:
        # Truncate to 8 decimals, as ccxt does for order amounts.
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
        self.orders.append((pair, order_type, side, amount))
        return {"id": "order-1", "status": "open"}


@pytest.fixture
def live_kraken(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FakeExchange:
    entry = get_entry("kraken")
    monkeypatch.setenv(entry.env_key, "test-key")
    monkeypatch.setenv(entry.env_secret, "test-secret")
    monkeypatch.setenv("WORLDWIDE_TRADING_ACK", "1")
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    # H2: live orders need the owner's approval in the host store, not an env flag.
    ExchangeControlStore(tmp_path / "exchange_control.db").approve_go_live("kraken")
    fake = FakeExchange()
    wrapped = SerializedExchange(fake)
    monkeypatch.setattr(GenericCcxtTradingAdapter, "_client", lambda self: wrapped)
    return fake


def test_live_order_is_sized_in_base_units(live_kraken: FakeExchange) -> None:
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert len(live_kraken.orders) == 1
    _, _, side, amount = live_kraken.orders[0]
    assert side == "buy"
    assert amount == pytest.approx(0.0005)  # $25 at $50,000, not 25 BTC
    assert result["sizing"] == "priced"
    assert result["price"] == pytest.approx(50_000.0)
    assert result["amount"] == pytest.approx(0.0005)


def test_mid_price_is_used_when_last_is_missing(live_kraken: FakeExchange) -> None:
    live_kraken.last = None
    live_kraken.bid, live_kraken.ask = 49_000.0, 51_000.0
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert result["price"] == pytest.approx(50_000.0)
    assert live_kraken.orders[0][3] == pytest.approx(0.0005)


def test_unusable_ticker_sends_no_order(live_kraken: FakeExchange) -> None:
    live_kraken.last = 0.0
    with pytest.raises(ValueError, match="no usable ticker price"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert live_kraken.orders == []


def test_stale_ticker_sends_no_order(live_kraken: FakeExchange) -> None:
    live_kraken.timestamp = time.time() * 1000 - 120_000
    with pytest.raises(ValueError, match="from the local clock"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert live_kraken.orders == []


def test_ticker_without_timestamp_sends_no_order(live_kraken: FakeExchange) -> None:
    live_kraken.timestamp = None
    with pytest.raises(ValueError, match="no timestamp"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert live_kraken.orders == []


def test_ticker_failure_sends_no_order(live_kraken: FakeExchange) -> None:
    live_kraken.ticker_error = RuntimeError("exchange unavailable")
    with pytest.raises(RuntimeError, match="exchange unavailable"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert live_kraken.orders == []


def test_order_below_minimum_amount_is_not_sent(live_kraken: FakeExchange) -> None:
    live_kraken.min_cost = None
    with pytest.raises(ValueError, match="below the exchange minimum"):
        route_order("kraken", "BTC/USD", "buy", 1.0, dry_run=False)  # 0.00002 BTC
    assert live_kraken.orders == []


def test_order_below_minimum_cost_is_not_sent(live_kraken: FakeExchange) -> None:
    live_kraken.min_amount = None
    with pytest.raises(ValueError, match="minimum cost"):
        route_order("kraken", "BTC/USD", "buy", 2.0, dry_run=False)  # $2 < $5 minimum
    assert live_kraken.orders == []


def test_dry_run_never_touches_the_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    def _no_exchange(self: GenericCcxtTradingAdapter) -> Any:
        raise AssertionError("dry run must not call the exchange")

    monkeypatch.setattr(GenericCcxtTradingAdapter, "_client", _no_exchange)
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=True)
    assert result["status"] == "simulated"
    assert result["sizing"] == "unpriced_dry_run"
