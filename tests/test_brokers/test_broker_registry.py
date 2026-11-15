"""TradFi broker registry is separate from CEX CCXT."""

from __future__ import annotations

from trendalgo.brokers.registry import (
    clear_broker_registry_cache,
    list_brokers,
    load_broker_registry,
)


def setup_function() -> None:
    clear_broker_registry_cache()


def test_alpaca_is_default_paper_broker() -> None:
    reg = load_broker_registry()
    assert reg.default_broker == "alpaca"
    alpaca = reg.by_id("alpaca")
    assert alpaca is not None
    assert alpaca.paper_enabled
    assert not alpaca.live_enabled
    assert alpaca.lane == "tradfi"
    assert "us_equity" in alpaca.asset_classes


def test_list_brokers_nonempty() -> None:
    assert len(list_brokers()) >= 1
