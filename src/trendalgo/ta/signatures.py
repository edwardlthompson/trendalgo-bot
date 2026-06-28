"""Shared TA cache key types — avoids circular imports between cache tiers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OhlcvSignature:
    bar_count: int
    first_ts: int
    last_ts: int

    @classmethod
    def from_ohlcv(cls, ohlcv: list[dict[str, Any]]) -> OhlcvSignature:
        if not ohlcv:
            return cls(0, 0, 0)
        return cls(len(ohlcv), int(ohlcv[0]["time"]), int(ohlcv[-1]["time"]))


def canonical_ta_params_hash(params: dict[str, Any]) -> str:
    def normalize(value: Any) -> Any:
        if isinstance(value, float) and value == int(value):
            return int(value)
        return value

    canonical = {str(k): normalize(v) for k, v in sorted(params.items())}
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
