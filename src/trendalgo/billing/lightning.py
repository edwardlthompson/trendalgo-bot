"""Optional Lightning invoice stub — user-initiated only (M7)."""

from __future__ import annotations

import hashlib
from typing import Any


def create_lightning_invoice(amount_usd: float, period: str) -> dict[str, Any]:
    seed = f"{period}:{amount_usd}:lightning"
    token = hashlib.sha256(seed.encode()).hexdigest()[:24]
    return {
        "invoice": f"lnbc{int(amount_usd * 100)}n1p{token}",
        "amount_usd": round(amount_usd, 2),
        "period": period,
        "user_initiated_only": True,
        "expires_in_seconds": 3600,
        "note": "Stub invoice for UX testing — not a live Lightning node.",
    }
