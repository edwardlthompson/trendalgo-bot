"""Solana wallet plugin: dry-run SOL + USDC; live path uses RPC helpers."""

from __future__ import annotations

from unittest.mock import patch

from trendalgo.venues.base import VenueEntry
from trendalgo.venues.plugins.solana import SolanaWalletReadPlugin


def _entry() -> VenueEntry:
    return VenueEntry(
        id="solana",
        brand="Solana",
        chain_type="solana",
        native_symbol="SOL",
        wallet_read_enabled=True,
        trading_enabled=False,
        rpc_env="SOLANA_RPC_URL",
        portfolio_plugins=(),
        swap_plugins=("jupiter",),
    )


def test_dry_run_returns_sol_and_usdc() -> None:
    plugin = SolanaWalletReadPlugin(_entry())
    rows = plugin.read_balances("9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin", dry_run=True)
    assets = {r.asset for r in rows}
    assert "SOL" in assets
    assert "USDC" in assets


def test_live_merges_spl_tokens(monkeypatch) -> None:  # noqa: ANN001
    plugin = SolanaWalletReadPlugin(_entry())
    monkeypatch.setenv("ONCHAIN_SYNC_ENABLED", "1")
    monkeypatch.setenv("SOLANA_RPC_URL", "https://example.invalid")
    with (
        patch("trendalgo.venues.plugins.solana.sol_balance", return_value=1.5),
        patch(
            "trendalgo.venues.plugins.solana.spl_token_balances",
            return_value=[("USDC", 10.0)],
        ),
    ):
        rows = plugin.read_balances("9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin", dry_run=False)
    by_asset = {r.asset: r for r in rows}
    assert by_asset["SOL"].quantity == 1.5
    assert by_asset["USDC"].quantity == 10.0
