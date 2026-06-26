"""Automated portfolio snapshots + daily notification job (P3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from trendalgo.notifications.daily_summary import format_daily_summary, send_daily_notification
from trendalgo.portfolio.alerts import check_portfolio_alerts
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.metrics import daily_pnl_from_curve, pl_breakdown
from trendalgo.portfolio.sync import sync_kraken_balances


def capture_portfolio_snapshot(
    store: PortfolioStore,
    *,
    dry_run: bool = True,
    on_log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    result = sync_kraken_balances(store, dry_run=dry_run)
    account_id = store.get_or_create_account("kraken", "default")
    curve = store.equity_curve(account_id)
    daily_pnl, _ = daily_pnl_from_curve(curve)
    snap = store.latest_snapshot(account_id)
    pl = pl_breakdown(snap["holdings"] if snap else [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store.upsert_daily_aggregate(
        account_id,
        today,
        float(result["total_usd"]),
        daily_pnl,
        pl.realized_usd,
        pl.unrealized_usd,
    )
    if on_log:
        on_log(f"portfolio snapshot: ${result['total_usd']}")
    return result


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
    except ImportError:
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: scheduled_portfolio_job(
            store, overview_builder, dry_run=dry_run, on_log=on_log
        ),
        "cron",
        hour=8,
        minute=0,
        id="trendalgo-portfolio-daily",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: capture_portfolio_snapshot(store, dry_run=dry_run, on_log=on_log),
        "interval",
        hours=6,
        id="trendalgo-portfolio-snapshot",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
