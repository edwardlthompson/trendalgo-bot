"""APScheduler scan jobs (O4)."""

from __future__ import annotations

from typing import Callable

from trendalgo.scanner.alerts import emit_alerts_for_snapshot
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.store import ScannerStore


def run_scheduled_scan(store: ScannerStore, on_log: Callable[[str], None] | None = None) -> int:
    settings = store.get_settings()
    snapshot = run_pipeline(settings)
    scan_id = store.save_snapshot(snapshot)
    emit_alerts_for_snapshot(store, snapshot)
    if on_log:
        on_log(f"scanner scan complete: {len(snapshot.opportunities)} opportunities")
    return scan_id


def start_scheduler(store: ScannerStore, on_log: Callable[[str], None] | None = None) -> object | None:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        return None

    settings = store.get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: run_scheduled_scan(store, on_log),
        "interval",
        minutes=settings.interval_minutes,
        id="trendalgo-scanner",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
