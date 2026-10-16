"""Plan allocation: the bots' equity caps must fit host equity times the max exposure (R4)."""

from __future__ import annotations

import math
from collections.abc import Iterable


def allocation_error(
    bot_caps_usd: Iterable[float], host_equity_usd: float, max_exposure_pct: float
) -> str | None:
    """None when the plan fits; otherwise the reason it is rejected. Checked at boot and each pass."""
    caps = list(bot_caps_usd)
    if any(not math.isfinite(cap) or cap < 0 for cap in caps):
        return "allocation rejected: a bot cap is negative or not a number"
    limit = max(0.0, host_equity_usd) * max_exposure_pct
    total = sum(caps)
    if total > limit:
        return (
            f"allocation rejected: caps total {total:.2f} exceed {limit:.2f} "
            f"(host equity {host_equity_usd:.2f} x max exposure {max_exposure_pct:.2f})"
        )
    return None
