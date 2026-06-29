"""On-chain + sentiment data module stub (T28)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any


def onchain_sentiment_stub(asset: str) -> dict[str, Any]:
    """Return placeholder on-chain activity + sentiment scores (no paid feeds)."""
    asset = asset.upper().strip()
    seed = int(hashlib.sha256(asset.encode()).hexdigest()[:8], 16)
    onchain_score = round((seed % 100) / 100.0, 3)
    sentiment_score = round(((seed >> 8) % 100) / 100.0, 3)
    return {
        "asset": asset,
        "onchain_activity_score": onchain_score,
        "sentiment_score": sentiment_score,
        "sources": ["stub"],
        "paid_indexers": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prototype": True,
    }
