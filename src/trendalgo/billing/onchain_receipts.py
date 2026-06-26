"""On-chain verifiable fee receipts — optional DeFi settlement path (#20)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any


def issue_fee_receipt(
    period: str,
    amount_usd: float,
    *,
    wallet: str | None = None,
    chain: str = "ethereum",
) -> dict[str, Any]:
    """Create a deterministic receipt payload for manual on-chain settlement."""
    if amount_usd < 0:
        raise ValueError("amount_usd must be non-negative")
    digest = hashlib.sha256(f"{period}:{amount_usd}:{wallet or ''}".encode()).hexdigest()
    receipt_id = f"rcpt-{digest[:16]}"
    return {
        "receipt_id": receipt_id,
        "period": period,
        "amount_usd": round(amount_usd, 2),
        "wallet": wallet,
        "chain": chain,
        "verification_hash": digest,
        "settlement_path": "manual_onchain_optional",
        "issued_at": datetime.now(UTC).isoformat(),
        "verifiable": True,
    }


def verify_fee_receipt(receipt_id: str, tx_hash: str, expected_hash: str) -> dict[str, Any]:
    """Stub verifier — checks receipt id prefix and non-empty tx hash."""
    ok = receipt_id.startswith("rcpt-") and len(tx_hash) >= 8
    hash_ok = hashlib.sha256(tx_hash.encode()).hexdigest().startswith(expected_hash[:8])
    return {
        "receipt_id": receipt_id,
        "tx_hash": tx_hash,
        "verified": ok and hash_ok,
        "on_chain_stub": True,
    }
