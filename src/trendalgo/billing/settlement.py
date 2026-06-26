"""User-initiated settlement helpers (M7, M22)."""

from __future__ import annotations

import os
from typing import Any


def settlement_address() -> str:
    return os.environ.get("TRENDALGO_SETTLEMENT_ADDRESS", "bc1q-trendalgo-settlement-sample")


def settlement_info(amount_usd: float, period: str) -> dict[str, Any]:
    return {
        "period": period,
        "amount_usd": round(amount_usd, 2),
        "asset": os.environ.get("TRENDALGO_SETTLEMENT_ASSET", "BTC"),
        "address": settlement_address(),
        "user_initiated_only": True,
        "auto_withdraw": False,
        "copy_label": f"TrendAlgo license {period}",
        "qr_payload": f"bitcoin:{settlement_address()}?amount={amount_usd}",
        "disclaimer": "Copy address and pay from your own wallet. TrendAlgo never holds withdrawal keys.",
    }
