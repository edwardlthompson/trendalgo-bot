"""Portfolio drawdown from equity curve (P11)."""

from __future__ import annotations

from typing import Any


def max_drawdown(curve: list[dict[str, Any]]) -> float:
    if not curve:
        return 0.0
    peak = float(curve[0]["total_usd"])
    max_dd = 0.0
    for point in curve:
        value = float(point["total_usd"])
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak else 0.0
        if dd > max_dd:
            max_dd = dd
    return round(max_dd, 4)
