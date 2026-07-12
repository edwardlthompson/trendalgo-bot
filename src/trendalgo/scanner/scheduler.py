"""APScheduler scan jobs (O4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from trendalgo.scanner.alerts import AlertSink, emit_alerts_for_snapshot
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.store import ScannerStore


def run_scheduled_scan(
    store: ScannerStore,
    on_log: Callable[[str], None] | None = None,
    on_alert: AlertSink | None = None,
) -> int:
    settings = store.get_settings()
    snapshot = run_pipeline(settings, store=store)
    scan_id = store.save_snapshot(snapshot)
    if not snapshot.degraded:
        emit_alerts_for_snapshot(store, snapshot, on_alert)
    if on_log:
        status = "degraded" if snapshot.degraded else "live"
        on_log(f"scanner scan complete ({status}): {len(snapshot.opportunities)} opportunities")
    return scan_id


def start_scheduler(
    store: ScannerStore,
    on_log: Callable[[str], None] | None = None,
    on_alert: AlertSink | None = None,
) -> object | None:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        return None

    settings = store.get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: run_scheduled_scan(store, on_log, on_alert),
        "interval",
        minutes=settings.interval_minutes,
        id="trendalgo-scanner",
        replace_existing=True,
    )
    scheduler.start()
    return cast(object, scheduler)
