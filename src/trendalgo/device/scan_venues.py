"""Which exchanges can be scanned (vault keys ∩ registry)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trendalgo.device.secrets_vault import VaultSecretStore
from trendalgo.exchanges.registry import ExchangeEntry, load_registry


@dataclass(frozen=True)
class ScanVenue:
    exchange_id: str
    brand: str
    max_private_calls_per_min: int


def vaulted_scan_venues(store: VaultSecretStore | None = None) -> list[ScanVenue]:
    """Venues with saved API keys that the scanner checklist can select."""
    vault = store or VaultSecretStore()
    vault.bind_registry()
    out: list[ScanVenue] = []
    for entry in load_registry().exchanges:
        if not (entry.portfolio_enabled or entry.trading_enabled):
            continue
        if vault.read_entry(entry.id) is None:
            continue
        out.append(
            ScanVenue(
                exchange_id=entry.id,
                brand=entry.brand,
                max_private_calls_per_min=int(entry.max_private_calls_per_min or 15),
            )
        )
    return out


def resolve_scan_exchange_ids(
    filters: dict[str, Any],
    *,
    store: VaultSecretStore | None = None,
) -> list[str]:
    """Selected scan venues that still have keys; empty → no scan."""
    vaulted = {v.exchange_id: v for v in vaulted_scan_venues(store)}
    raw = filters.get("scan_exchanges")
    if isinstance(raw, list) and raw:
        wanted = [str(x).strip().lower() for x in raw if str(x).strip()]
        return [eid for eid in wanted if eid in vaulted]
    # Legacy: single exchange brand / All.
    legacy = str(filters.get("exchange") or "All").strip().lower()
    if legacy in ("", "all"):
        return list(vaulted.keys())
    aliases = {
        "kraken": "kraken",
        "coinbase": "coinbaseadvanced",
        "coinbaseadvanced": "coinbaseadvanced",
    }
    eid = aliases.get(legacy, legacy)
    return [eid] if eid in vaulted else []


def registry_entry(exchange_id: str) -> ExchangeEntry | None:
    return load_registry().by_id(exchange_id)
