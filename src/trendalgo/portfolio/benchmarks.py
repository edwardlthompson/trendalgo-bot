"""BTC/ETH benchmark overlay (P8)."""

from __future__ import annotations

from typing import Any


def benchmark_curves(equity_curve: list[dict[str, Any]]) -> dict[str, list[dict[str, float]]]:
    """Synthetic benchmark curves aligned to portfolio equity timestamps."""
    if not equity_curve:
        return {"btc": [], "eth": []}
    base = float(equity_curve[0]["total_usd"])
    btc: list[dict[str, float]] = []
    eth: list[dict[str, float]] = []
    for i, point in enumerate(equity_curve):
        ts = int(point["time"])
        drift_btc = 1 + 0.0008 * i
        drift_eth = 1 + 0.0005 * i
        btc.append({"time": ts, "value": round(base * drift_btc, 2)})
        eth.append({"time": ts, "value": round(base * drift_eth, 2)})
    return {"btc": btc, "eth": eth}
