"""Automated portfolio snapshots + daily notification job (P3)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from trendalgo.notifications.daily_summary import format_daily_summary, send_daily_notification
from trendalgo.portfolio.alerts import check_portfolio_alerts
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.metrics import daily_pnl_from_curve, pl_breakdown
from trendalgo.portfolio.multi_exchange import aggregate_holdings, sync_all_exchanges
from trendalgo.portfolio.performance import (
    curve_for_metrics,
    ensure_btc_dry_run_fixture,
    performance_curve,
)


def capture_portfolio_snapshot(
    store: PortfolioStore,
    *,
    dry_run: bool = True,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Sync all exchanges, record today's aggregate on the primary account."""
    sync_all_exchanges(store, dry_run=dry_run)
    account_id = store.get_or_create_account("kraken", "default")
    if dry_run:
        ensure_btc_dry_run_fixture(store, account_id)
    aggregated = aggregate_holdings(store)
    total_usd = float(aggregated["total_usd"])
    curve = curve_for_metrics(performance_curve(store, account_id, "7d"))
    daily_pnl, _ = daily_pnl_from_curve(curve)
    snap = store.latest_snapshot(account_id)
    pl = pl_breakdown(snap["holdings"] if snap else aggregated["holdings"])
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    store.upsert_daily_aggregate(
        account_id,
        today,
        total_usd,
        daily_pnl,
        pl.realized_usd,
        pl.unrealized_usd,
    )
    if on_log:
        on_log(f"portfolio snapshot (all exchanges): ${total_usd}")
    return {
        "account_id": account_id,
        "total_usd": total_usd,
        "mode": "dry-run" if dry_run else "live",
        "exchange_count": aggregated["exchange_count"],
    }


def run_daily_notification(
    store: PortfolioStore,
    overview: dict[str, Any],
    *,
    dry_run: bool = True,
) -> bool:
    text = format_daily_summary(overview)
    store.insert_notification("daily_pl", "Daily P/L summary", text)
    return send_daily_notification(text, dry_run=dry_run)


def scheduled_portfolio_job(
    store: PortfolioStore,
    overview_builder: Callable[[], dict[str, Any]],
    *,
    dry_run: bool = True,
    on_log: Callable[[str], None] | None = None,
) -> None:
    capture_portfolio_snapshot(store, dry_run=dry_run, on_log=on_log)
    overview = overview_builder()
    check_portfolio_alerts(store, store.get_or_create_account("kraken", "default"), overview)
    run_daily_notification(store, overview, dry_run=dry_run)


def start_portfolio_scheduler(
    store: PortfolioStore,
    overview_builder: Callable[[], dict[str, Any]],
    *,
    dry_run: bool = True,
    on_log: Callable[[str], None] | None = None,
) -> object | None:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        return None

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: scheduled_portfolio_job(store, overview_builder, dry_run=dry_run, on_log=on_log),
        CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="trendalgo-portfolio-daily",
        replace_existing=True,
    )
    scheduler.start()
    return cast(object, scheduler)
