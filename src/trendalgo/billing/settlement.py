"""User-initiated settlement address helpers (M7, M22)."""

from __future__ import annotations

from trendalgo.billing.settlement_assets import (
    list_available_assets,
    recipient_for_asset,
    settlement_btc_address,
    settlement_evm_address,
)

__all__ = [
    "list_available_assets",
    "recipient_for_asset",
    "settlement_address",
    "settlement_evm_address",
    "settlement_info",
]


def settlement_address() -> str:
    return settlement_btc_address()


def settlement_info(amount_usd: float, period: str) -> dict[str, object]:
    """Display payload for user-initiated settlement (no auto-withdraw)."""
    return {
        "amount_usd": amount_usd,
        "period": period,
        "btc_address": settlement_btc_address(),
        "evm_address": settlement_evm_address(),
        "user_initiated_only": True,
        "auto_withdraw": False,
    }
