"""Portfolio performance curves from Kraken market data (daily / hourly)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from trendalgo.market.portfolio_curves import btc_portfolio_curve, token_closes_for_range
from trendalgo.market.service import HOURLY_RANGES
from trendalgo.market.synthetic import btc_usd_price_at
from trendalgo.portfolio.db import HoldingRow, PortfolioStore
from trendalgo.portfolio.top10_benchmark import TOP10_SYMBOLS, compare_to_top10, top10_index_curve

BTC_QTY = 1.0
MIN_HISTORY_DAYS = 30

# Re-export for tests and callers.
PERFORMANCE_RANGES = {
    "1y": timedelta(days=365),
    "6m": timedelta(days=182),
    "3m": timedelta(days=91),
    "1m": timedelta(days=30),
    "14d": timedelta(days=14),
    "7d": timedelta(days=7),
    "24h": timedelta(hours=24),
}


def _holding_row_at(ts: datetime) -> HoldingRow:
    price = btc_usd_price_at(ts)
    cost = btc_usd_price_at(ts - timedelta(days=365))
    return HoldingRow(
        asset="BTC",
        quantity=BTC_QTY,
        price_usd=price,
        value_usd=round(BTC_QTY * price, 2),
        cost_basis_usd=round(BTC_QTY * cost, 2),
    )


def current_btc_holding() -> HoldingRow:
    return _holding_row_at(datetime.now(UTC))


def ensure_btc_dry_run_fixture(store: PortfolioStore, account_id: int) -> bool:
    """Seed 1 BTC + 1 year of daily aggregates from market or synthetic closes."""
    if os.environ.get("TRENDALGO_STRESS_PORTFOLIO", "").lower() in {"1", "true", "yes"}:
        return False
    if not _needs_history_seed(store, account_id):
        return False
    store.clear_daily_aggregates(account_id)
    now = datetime.now(UTC).replace(microsecond=0)
    points = btc_portfolio_curve("1y", quantity=BTC_QTY, now=now)
    prev_total = 0.0
    for point in points:
        ts = datetime.fromtimestamp(int(point["time"]), tz=UTC)
        day = ts.strftime("%Y-%m-%d")
        total = float(point["value"])
        daily_pnl = round(total - prev_total, 2) if prev_total else 0.0
        unrealized = round(total - _holding_row_at(ts).cost_basis_usd, 2)
        store.upsert_daily_aggregate(account_id, day, total, daily_pnl, 0.0, unrealized)
        prev_total = total
    holding = _holding_row_at(now)
    store.insert_snapshot_at(
        account_id,
        holding.value_usd,
        [holding],
        captured_at=now.isoformat(),
        source="dry-run-btc-1y-fixture",
    )
    return True


def _needs_history_seed(store: PortfolioStore, account_id: int) -> bool:
    count = store.count_daily_aggregates(account_id)
    if count < MIN_HISTORY_DAYS:
        return True
    start = (datetime.now(UTC) - timedelta(days=365)).date().isoformat()
    rows = store.list_daily_aggregates_since(account_id, start)
    return len(rows) < MIN_HISTORY_DAYS


def list_history_dates(store: PortfolioStore, account_id: int, *, limit: int = 365) -> list[str]:
    rows = store.list_daily_aggregates(account_id, limit=limit)
    dates = [str(r["date"]) for r in rows]
    dates.reverse()
    return dates


def build_performance_payload(
    store: PortfolioStore,
    account_id: int,
    range_key: str,
    *,
    dry_run: bool = True,
) -> dict[str, Any]:
    if dry_run:
        ensure_btc_dry_run_fixture(store, account_id)
    points = performance_curve(store, account_id, range_key)
    token_closes = token_closes_for_range(TOP10_SYMBOLS, range_key)
    top10 = top10_index_curve(points, token_closes=token_closes)
    comparison = compare_to_top10(points, top10)
    return {
        "range": range_key,
        "granularity": "1h" if range_key in HOURLY_RANGES else "1d",
        "source": "kraken",
        "points": points,
        "top10_index": top10,
        "comparison": comparison,
        "top10_symbols": list(TOP10_SYMBOLS),
    }


def performance_curve(
    store: PortfolioStore,
    account_id: int,
    range_key: str,
    *,
    now: datetime | None = None,
) -> list[dict[str, float | int]]:
    if range_key not in PERFORMANCE_RANGES:
        raise KeyError(f"unknown performance range: {range_key}")
    anchor = (now or datetime.now(UTC)).replace(microsecond=0)
    return btc_portfolio_curve(range_key, quantity=BTC_QTY, now=anchor)


def curve_for_metrics(points: list[dict[str, float | int]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in points:
        ts = datetime.fromtimestamp(int(p["time"]), tz=UTC)
        out.append(
            {
                "time": int(p["time"]),
                "total_usd": float(p["value"]),
                "captured_at": ts.isoformat(),
            }
        )
    return out
