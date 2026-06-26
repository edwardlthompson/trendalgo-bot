"""DEX trading gates — DEX_TRADING_ACK (S23) + live gates (S24, CM-10)."""

from __future__ import annotations

import os

from trendalgo.dex.control import DexVenueControlStore
from trendalgo.dex.signer import signer_configured
from trendalgo.venues.registry import get_venue


def validate_dex_swap_access(*, app_dry_run: bool, live_swap: bool = False) -> None:
    """Dry-run swap access; live swaps delegate to validate_live_swap_gates."""
    if live_swap:
        return
    if app_dry_run:
        return
    if os.environ.get("DEX_TRADING_ACK") != "1":
        raise ValueError(
            "DEX swap endpoints require DEX_TRADING_ACK=1 when bot is not in dry-run mode"
        )


def validate_live_swap_gates(
    venue_id: str,
    control: DexVenueControlStore,
    *,
    slippage_bps: int,
) -> None:
    """Hard gates for live DEX swap broadcast (H-036, CM-9, CM-10)."""
    entry = get_venue(venue_id)
    if not entry.trading_enabled:
        raise ValueError(f"venue trading not enabled in registry: {venue_id}")
    if os.environ.get("DEX_LIVE_TRADING_ACK") != "1":
        raise ValueError("H-036: live DEX swaps require DEX_LIVE_TRADING_ACK=1 on VPS")
    if os.environ.get("GO_LIVE_APPROVED") != "1":
        raise ValueError("GO_LIVE_APPROVED=1 required for live DEX swaps")
    if not signer_configured():
        raise ValueError("DEX_SIGNER_KEY required on VPS for live swaps (CM-9)")
    max_slip = int(os.environ.get("DEX_MAX_SLIPPAGE_BPS", "100"))
    if slippage_bps < 0 or slippage_bps > max_slip:
        raise ValueError(f"slippage_bps must be 0–{max_slip}")
    ok, reason = control.can_execute(venue_id, live=True)
    if not ok:
        raise ValueError(reason)
