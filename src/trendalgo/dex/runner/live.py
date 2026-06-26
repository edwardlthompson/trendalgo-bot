"""Live DEX swap runner — swap-only, no transfer/withdraw (S24, CM-11)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trendalgo.dex.control import DexVenueControlStore
from trendalgo.dex.gates import validate_live_swap_gates
from trendalgo.dex.nonce import NonceStore
from trendalgo.dex.signer import sign_swap_payload, signer_fingerprint
from trendalgo.venues.registry import get_swap_plugin, get_venue, load_venue_registry


@dataclass
class LiveSwapRunner:
    """Execute registry-driven live swaps — signer env on VPS only (CM-9)."""

    control: DexVenueControlStore
    nonce_store: NonceStore
    _history: list[dict[str, Any]] = field(default_factory=list)

    def execute(
        self,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
        *,
        slippage_bps: int = 50,
    ) -> dict[str, Any]:
        if sell_amount <= 0:
            raise ValueError("sell_amount must be positive")
        venue_id = chain.strip().lower()
        validate_live_swap_gates(venue_id, self.control, slippage_bps=slippage_bps)
        entry = get_venue(venue_id)
        plugin = get_swap_plugin(venue_id)
        nonce = self.nonce_store.next_nonce(venue_id)
        payload = f"{venue_id}:{sell_token}:{buy_token}:{sell_amount}:{nonce}:{slippage_bps}"
        signed_tx_hash = sign_swap_payload(payload)
        result = plugin.execute_live_swap(
            sell_token,
            buy_token,
            sell_amount,
            slippage_bps=slippage_bps,
            nonce=nonce,
            signed_tx_hash=signed_tx_hash,
        )
        result["signer_fingerprint"] = signer_fingerprint()
        result["registry_version"] = load_venue_registry().version
        result["trading_enabled"] = entry.trading_enabled
        self._history.append(result)
        return result

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)
