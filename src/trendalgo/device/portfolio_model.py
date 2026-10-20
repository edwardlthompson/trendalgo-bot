"""Pure rules for the device Portfolio page: path resolve and a read-only overview."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.device.portfolio_compare import local_comparison_curves
from trendalgo.device.profile import PORTFOLIO_DB, PORTFOLIO_ENV, shared_data_dir
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.drawdown import max_drawdown
from trendalgo.portfolio.health import health_score
from trendalgo.portfolio.metrics import (
    allocation_rows,
    daily_pnl_from_curve,
    enrich_holdings,
    pl_breakdown,
)
from trendalgo.portfolio.multi_exchange import aggregate_holdings
from trendalgo.portfolio.performance import PERFORMANCE_RANGES
from trendalgo.portfolio.rebalance import rebalance_suggestions


@dataclass(frozen=True)
class PortfolioOverview:
    net_worth_usd: float
    daily_pnl_usd: float
    daily_pnl_pct: float
    realized_usd: float
    unrealized_usd: float
    total_pl_usd: float
    health: int
    max_drawdown_pct: float
    captured_at: str
    source: str
    holdings: list[dict[str, Any]]
    allocation: list[dict[str, Any]]
    equity: list[dict[str, Any]]  # oldest-first: date, total_usd
    path: Path
    snapshot_dates: tuple[str, ...] = ()
    compare_top10: tuple[dict[str, Any], ...] = ()
    compare_buy_hold: tuple[dict[str, Any], ...] = ()
    accounts: tuple[dict[str, Any], ...] = ()
    tags: dict[str, str] | None = None
    rebalance: tuple[dict[str, Any], ...] = ()
    realized_available: bool = False
    nft_status: str = "untracked"


def portfolio_db_path(root: Path) -> Path | None:
    """An existing portfolio file, or None. Prefers the launcher copy under TRENDALGO_DATA_DIR."""
    override = os.environ.get(PORTFOLIO_ENV, "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    data = shared_data_dir()
    if data is not None:
        launcher = data / "launcher" / PORTFOLIO_DB
        if launcher.is_file():
            return launcher
        shared = data / PORTFOLIO_DB
        if shared.is_file():
            return shared
    local = root / PORTFOLIO_DB
    return local if local.is_file() else None


def load_overview(path: Path, *, as_of_date: str | None = None) -> PortfolioOverview | None:
    """Read a snapshot and equity history. Returns None when the file has no account yet."""
    store = PortfolioStore(path, create=False)
    account_id = _primary_account_id(store)
    if account_id is None:
        return None
    aggregated = aggregate_holdings(store)
    accounts_raw = list(store.list_accounts())
    use_agg = len(accounts_raw) >= 2 and as_of_date is None
    if use_agg and aggregated.get("holdings"):
        net = float(aggregated["total_usd"])
        raw_holdings = list(aggregated["holdings"])
        source = "multi_exchange"
        captured_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    else:
        snap = _snapshot_for_date(store, account_id, as_of_date)
        if snap is None:
            return None
        if str(snap.get("source") or "").startswith("dry-run") and len(accounts_raw) > 1:
            # Prefer live multi-account over a dry-run BTC fixture masking real sync.
            if aggregated.get("holdings"):
                net = float(aggregated["total_usd"])
                raw_holdings = list(aggregated["holdings"])
                source = "multi_exchange"
                captured_at = datetime.now(UTC).replace(microsecond=0).isoformat()
            else:
                net = float(snap["total_usd"])
                raw_holdings = list(snap["holdings"])
                source = str(snap["source"])
                captured_at = str(snap["captured_at"])
        else:
            net = float(snap["total_usd"])
            raw_holdings = list(snap["holdings"])
            source = str(snap["source"])
            captured_at = str(snap["captured_at"])
    holdings = enrich_holdings(raw_holdings)
    pl = pl_breakdown(holdings)
    equity = _equity_curve(store, account_id, net, captured_at)
    daily_usd, daily_pct = daily_pnl_from_curve(equity)
    top10, buy_hold = local_comparison_curves(equity)
    dates = tuple(store.list_snapshot_dates(account_id, limit=90))
    allocation = allocation_rows(holdings, net)
    dd = max_drawdown(equity)
    health = health_score(allocation, dd, daily_pct)
    tags = store.get_asset_tags()
    for row in holdings:
        asset = str(row.get("asset") or "")
        if asset in tags:
            row["tag"] = tags[asset]
        alloc = next((a for a in allocation if a["asset"] == asset), None)
        row["allocation_pct"] = float(alloc["pct"]) if alloc else 0.0
    targets = _load_targets(store, account_id)
    rebalance = tuple(rebalance_suggestions(allocation, targets, net)) if targets else ()
    accounts = tuple(
        {
            "id": int(a["id"]),
            "exchange": str(a.get("exchange") or ""),
            "label": str(a.get("label") or ""),
        }
        for a in accounts_raw
    )
    return PortfolioOverview(
        net_worth_usd=net,
        daily_pnl_usd=daily_usd,
        daily_pnl_pct=daily_pct,
        realized_usd=pl.realized_usd,
        unrealized_usd=pl.unrealized_usd,
        total_pl_usd=pl.total_usd,
        health=health,
        max_drawdown_pct=dd,
        captured_at=captured_at,
        source=source,
        holdings=holdings,
        allocation=allocation,
        equity=equity,
        path=path,
        snapshot_dates=dates,
        compare_top10=tuple(top10),
        compare_buy_hold=tuple(buy_hold),
        accounts=accounts,
        tags=tags,
        rebalance=rebalance,
        realized_available=pl.realized_available,
        nft_status="untracked",
    )


def equity_for_range(path: Path, range_key: str) -> list[dict[str, Any]]:
    """Slice local equity aggregates for chart range tabs (1y|6m|…)."""
    if range_key not in PERFORMANCE_RANGES:
        range_key = "1y"
    store = PortfolioStore(path, create=False)
    account_id = _primary_account_id(store)
    if account_id is None:
        return []
    days = int(PERFORMANCE_RANGES[range_key].total_seconds() // 86400) or 365
    cutoff = datetime.now(UTC).date() - timedelta(days=days)
    points: list[dict[str, Any]] = []
    for row in reversed(store.list_daily_aggregates(account_id, limit=max(days, 30))):
        day = str(row["date"])
        try:
            parsed = datetime.fromisoformat(day).date()
        except ValueError:
            continue
        if parsed < cutoff:
            continue
        points.append({"captured_at": day, "total_usd": float(row["total_usd"])})
    return points


def _load_targets(store: PortfolioStore, account_id: int) -> list[dict[str, Any]]:
    try:
        return list(store.list_allocation_targets(account_id))
    except Exception:
        return []


def _primary_account_id(store: PortfolioStore) -> int | None:
    accounts = store.list_accounts()
    if not accounts:
        return None
    account_id = int(accounts[0]["id"])
    for account in accounts:
        if account.get("exchange") == "kraken":
            return int(account["id"])
    return account_id


def _snapshot_for_date(
    store: PortfolioStore, account_id: int, as_of_date: str | None
) -> dict[str, Any] | None:
    if as_of_date:
        by_date = store.snapshot_by_date(account_id, as_of_date)
        return dict(by_date) if by_date is not None else None
    latest = store.latest_snapshot(account_id)
    return dict(latest) if latest is not None else None


def _equity_curve(
    store: PortfolioStore, account_id: int, net_worth: float, captured_at: str
) -> list[dict[str, Any]]:
    rows = store.list_daily_aggregates(account_id, limit=365)
    if not rows:
        return [{"captured_at": captured_at, "total_usd": net_worth}]
    # list_daily_aggregates is newest-first; charts want oldest-first.
    points = [
        {"captured_at": str(r["date"]), "total_usd": float(r["total_usd"])} for r in reversed(rows)
    ]
    return points
