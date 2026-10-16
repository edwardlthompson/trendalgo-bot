"""Local-only portfolio benchmark curves (synthetic prices, no network)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trendalgo.market.synthetic import btc_usd_price_at
from trendalgo.portfolio.top10_benchmark import top10_index_curve


def local_comparison_curves(
    equity: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    perf = _equity_perf_points(equity)
    if len(perf) < 2:
        return [], []
    top10_raw = top10_index_curve(perf)
    bh_raw = _btc_buy_hold_curve(perf)
    return _align_curve(top10_raw, equity), _align_curve(bh_raw, equity)


def _equity_perf_points(equity: list[dict[str, Any]]) -> list[dict[str, float | int]]:
    out: list[dict[str, float | int]] = []
    for point in equity:
        ts = epoch_seconds(str(point.get("captured_at", "")))
        if ts is None:
            continue
        out.append({"time": ts, "value": float(point["total_usd"])})
    return out


def _btc_buy_hold_curve(points: list[dict[str, float | int]]) -> list[dict[str, float | int]]:
    first_ts = datetime.fromtimestamp(int(points[0]["time"]), tz=UTC)
    base_btc = btc_usd_price_at(first_ts)
    base_val = float(points[0]["value"])
    out: list[dict[str, float | int]] = []
    for point in points:
        ts = datetime.fromtimestamp(int(point["time"]), tz=UTC)
        ratio = btc_usd_price_at(ts) / base_btc if base_btc else 1.0
        out.append({"time": int(point["time"]), "value": round(base_val * ratio, 2)})
    return out


def _align_curve(
    perf: list[dict[str, float | int]], equity: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_time = {int(p["time"]): float(p["value"]) for p in perf}
    aligned: list[dict[str, Any]] = []
    for point in equity:
        ts = epoch_seconds(str(point.get("captured_at", "")))
        if ts is None or ts not in by_time:
            continue
        aligned.append({"captured_at": point["captured_at"], "total_usd": by_time[ts]})
    return aligned


def epoch_seconds(raw: str) -> int | None:
    if not raw:
        return None
    if len(raw) == 10 and raw[4] == "-":
        dt = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=UTC)
    else:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return int(dt.timestamp())
