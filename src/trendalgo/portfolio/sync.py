"""CCXT read-only Kraken balance sync (P4) — delegates to exchanges adapter (S13)."""

from __future__ import annotations

from trendalgo.exchanges.adapters.kraken import sync_kraken_balances

__all__ = ["sync_kraken_balances"]
