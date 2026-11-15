"""CEX-P4a: dry-run → live-gate smoke for Tier B; Tier C stays behind worldwide ack."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.exchanges.registry import get_entry
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.multi_exchange import route_order

# Roadmap Tier B — US portfolio venues with trading_enabled.
TIER_B_IDS: tuple[str, ...] = (
    "coinbaseadvanced",
    "gemini",
    "bitstamp",
    "cryptocom",
)
# Roadmap Tier C — us_restricted; live needs WORLDWIDE_TRADING_ACK=1.
TIER_C_IDS: tuple[str, ...] = ("binance", "bybit", "okx")


def smoke_dry_run(
    exchange_id: str, *, pair: str = "BTC/USD", amount: float = 25.0
) -> dict[str, Any]:
    """Simulate a Tier B/C order; never hits the network."""
    result = route_order(exchange_id, pair, "buy", amount, dry_run=True)
    if result.get("status") != "simulated":
        raise AssertionError(f"{exchange_id}: expected simulated dry-run, got {result!r}")
    return result


def smoke_live_refused_without_go_live(
    exchange_id: str,
    control: ExchangeControlStore,
    *,
    pair: str = "BTC/USD",
    amount: float = 25.0,
) -> str:
    """Live path must refuse until owner go-live (and keys / ack as applicable)."""
    try:
        route_order(exchange_id, pair, "buy", amount, dry_run=False, control=control)
    except ValueError as exc:
        return str(exc)
    raise AssertionError(f"{exchange_id}: live order must refuse without go-live")


def smoke_tier_c_legal_ack(control: ExchangeControlStore, exchange_id: str) -> str:
    """With go-live approved but no WORLDWIDE_TRADING_ACK, Tier C live must refuse."""
    if exchange_id not in TIER_C_IDS:
        raise ValueError(f"not a Tier C id: {exchange_id}")
    entry = get_entry(exchange_id)
    if not entry.us_restricted:
        raise AssertionError(f"{exchange_id}: expected us_restricted")
    control.approve_go_live(exchange_id)
    return smoke_live_refused_without_go_live(exchange_id, control)


def run_tier_b_smoke(control_db: Path) -> dict[str, Any]:
    """Full Tier B matrix: dry-run ok, live refused without go-live."""
    control = ExchangeControlStore(control_db)
    dry: dict[str, dict[str, Any]] = {}
    live_refusal: dict[str, str] = {}
    for eid in TIER_B_IDS:
        dry[eid] = smoke_dry_run(eid)
        live_refusal[eid] = smoke_live_refused_without_go_live(eid, control)
    return {"tier": "B", "dry_run": dry, "live_refusal": live_refusal}
