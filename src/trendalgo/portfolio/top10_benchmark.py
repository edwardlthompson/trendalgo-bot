"""Equal-weight top-10 crypto index benchmark."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trendalgo.market.synthetic import token_usd_price_at
from trendalgo.market.types import PricePoint

TOP10_SYMBOLS: tuple[str, ...] = (
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
    "ADA",
    "DOGE",
    "AVAX",
    "DOT",
    "LINK",
)


def _price_at_or_before(series: list[PricePoint], ts: int) -> float | None:
    if not series:
        return None
    lo, hi = 0, len(series) - 1
    best: float | None = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if series[mid].time <= ts:
            best = series[mid].close
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def top10_index_curve(
    portfolio_points: list[dict[str, float | int]],
    *,
    token_closes: dict[str, list[PricePoint]] | None = None,
    anchor: datetime | None = None,
) -> list[dict[str, float | int]]:
    """Cumulative equal-weight top-10 index aligned to portfolio timestamps."""
    if not portfolio_points:
        return []
    if token_closes:
        return _index_from_market(portfolio_points, token_closes)
    return _index_synthetic(portfolio_points, anchor=anchor)


def _index_from_market(
    portfolio_points: list[dict[str, float | int]],
    token_closes: dict[str, list[PricePoint]],
) -> list[dict[str, float | int]]:
    first_ts = int(portfolio_points[0]["time"])
    base_prices: dict[str, float] = {}
    for sym in TOP10_SYMBOLS:
        series = token_closes.get(sym, [])
        price = _price_at_or_before(series, first_ts)
        if price is not None and price > 0:
            base_prices[sym] = price
    portfolio_base = float(portfolio_points[0]["value"])
    out: list[dict[str, float | int]] = []
    for point in portfolio_points:
        ts = int(point["time"])
        ratios: list[float] = []
        for sym in TOP10_SYMBOLS:
            base = base_prices.get(sym)
            if not base:
                continue
            series = token_closes.get(sym, [])
            price = _price_at_or_before(series, ts)
            if price is not None and price > 0:
                ratios.append(price / base)
        avg_ratio = sum(ratios) / len(ratios) if ratios else 1.0
        out.append({"time": ts, "value": round(portfolio_base * avg_ratio, 2)})
    return out


def _index_synthetic(
    portfolio_points: list[dict[str, float | int]],
    *,
    anchor: datetime | None = None,
) -> list[dict[str, float | int]]:
    anchor = anchor or datetime.now(UTC)
    first_ts = int(portfolio_points[0]["time"])
    start = datetime.fromtimestamp(first_ts, tz=UTC)
    base_values = {sym: token_usd_price_at(sym, start, anchor=anchor) for sym in TOP10_SYMBOLS}
    portfolio_base = float(portfolio_points[0]["value"])
    out: list[dict[str, float | int]] = []
    for point in portfolio_points:
        ts = datetime.fromtimestamp(int(point["time"]), tz=UTC)
        ratios = [
            token_usd_price_at(sym, ts, anchor=anchor) / base_values[sym]
            for sym in TOP10_SYMBOLS
            if base_values[sym] > 0
        ]
        avg_ratio = sum(ratios) / len(ratios) if ratios else 1.0
        out.append({"time": int(point["time"]), "value": round(portfolio_base * avg_ratio, 2)})
    return out


def compare_to_top10(
    portfolio_points: list[dict[str, float | int]],
    index_points: list[dict[str, float | int]],
) -> dict[str, Any]:
    if len(portfolio_points) < 2 or len(index_points) < 2:
        return {"portfolio_return_pct": 0.0, "top10_return_pct": 0.0, "alpha_pct": 0.0}
    p0 = float(portfolio_points[0]["value"])
    p1 = float(portfolio_points[-1]["value"])
    i0 = float(index_points[0]["value"])
    i1 = float(index_points[-1]["value"])
    port_ret = ((p1 / p0) - 1) * 100 if p0 else 0.0
    idx_ret = ((i1 / i0) - 1) * 100 if i0 else 0.0
    return {
        "portfolio_return_pct": round(port_ret, 2),
        "top10_return_pct": round(idx_ret, 2),
        "alpha_pct": round(port_ret - idx_ret, 2),
        "symbols": list(TOP10_SYMBOLS),
    }
