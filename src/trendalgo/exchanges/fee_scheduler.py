"""Monthly exchange fee verification scheduler."""

from __future__ import annotations

from collections.abc import Callable

from trendalgo.exchanges.fee_store import FeeStore
from trendalgo.exchanges.fee_sync import sync_exchange_fees


def run_scheduled_fee_check(
    store: FeeStore,
    *,
    on_log: Callable[[str], None] | None = None,
) -> dict:
    on_log and on_log("exchange fees: monthly public fee-page verification starting")
    return sync_exchange_fees(store, on_log=on_log)


def start_fee_scheduler(
    store: FeeStore,
    *,
    on_log: Callable[[str], None] | None = None,
) -> object | None:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        return None

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: run_scheduled_fee_check(store, on_log=on_log),
        CronTrigger(day=1, hour=3, minute=0, timezone="UTC"),
        id="trendalgo-exchange-fees-monthly",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
