"""H2 at the order route: old env flags cannot enable live. Only the owner's approval can."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.exchanges.registry import get_entry
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.multi_exchange import route_order

OLD_FLAGS = {
    "GO_LIVE_APPROVED": "1",
    "WORLDWIDE_TRADING_ACK": "1",
    "TV_EXECUTION_ACK": "1",
    "DEX_LIVE_TRADING_ACK": "1",
}


class RecordingAdapter:
    """Stands in for the exchange adapter and records which call the route made."""

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def reference_price(self, pair: str) -> float:
        return 50_000.0

    def submit_order(self, pair: str, side: str, amount: float, price: float) -> dict[str, Any]:
        self.calls.append("submit")
        return {"status": "open", "order_id": "order-1", "amount": amount, "price": price}

    def simulate_order(self, pair: str, side: str, amount: float, price: float) -> dict[str, Any]:
        self.calls.append("simulate")
        return {"status": "simulated"}


@pytest.fixture
def host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[list[str], Path]:
    entry = get_entry("kraken")
    monkeypatch.setenv(entry.env_key, "test-key")
    monkeypatch.setenv(entry.env_secret, "test-secret")
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    calls: list[str] = []
    monkeypatch.setattr(
        "trendalgo.trading.multi_exchange.get_trading_adapter",
        lambda _exchange: RecordingAdapter(calls),
    )
    return calls, tmp_path


def test_old_flags_alone_never_enable_live(
    host: tuple[list[str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls, _ = host
    for name, value in OLD_FLAGS.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="go_live_required"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert calls == []


def test_owner_approval_enables_live_without_any_env_flag(host: tuple[list[str], Path]) -> None:
    calls, data_dir = host
    ExchangeControlStore(data_dir / "exchange_control.db").approve_go_live("kraken")
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert calls == ["submit"]
    assert result["sizing"] == "priced"


def test_a_paused_venue_refuses_live_even_when_approved(host: tuple[list[str], Path]) -> None:
    calls, data_dir = host
    store = ExchangeControlStore(data_dir / "exchange_control.db")
    store.approve_go_live("kraken")
    store.set_paused("kraken", True)
    with pytest.raises(ValueError, match="exchange_paused"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert calls == []


def test_missing_api_keys_refuse_live_instead_of_simulating(
    host: tuple[list[str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls, data_dir = host
    ExchangeControlStore(data_dir / "exchange_control.db").approve_go_live("kraken")
    monkeypatch.delenv(get_entry("kraken").env_key)
    with pytest.raises(ValueError, match="credentials_missing"):
        route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=False)
    assert calls == []


def test_dry_run_needs_no_approval(host: tuple[list[str], Path]) -> None:
    calls, _ = host
    result = route_order("kraken", "BTC/USD", "buy", 25.0, dry_run=True)
    assert calls == ["simulate"]
    assert result["sizing"] == "unpriced_dry_run"
