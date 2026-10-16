"""APScheduler scan jobs (O4)."""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any, cast

from trendalgo.scanner.alerts import AlertSink, emit_alerts_for_snapshot
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.progress import ScanProgress, get_scan_progress
from trendalgo.scanner.snapshot import QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


def _lts_enabled() -> bool:
    return os.environ.get("LTS_PUBLIC_SNAPSHOT_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _backtest_enabled() -> bool:
    return os.environ.get("BACKTEST_ENABLED", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _publish_lts(
    snapshot: QualifiedSnapshot,
    *,
    run_backtests: bool,
    final_results: list[dict[str, Any]] | None = None,
) -> None:
    from trendalgo.lts_vendor.bridge import publish_from_v2_snapshot

    publish_from_v2_snapshot(snapshot, run_backtests=run_backtests, final_results=final_results)


def run_scheduled_scan(
    store: ScannerStore,
    on_log: Callable[[str], None] | None = None,
    on_alert: AlertSink | None = None,
) -> int:
    """Run one scan. Returns once the LTS snapshot is published; backtests finish in the background.

    The run stays open in the progress feed until the background backtest job ends too.
    """
    progress = get_scan_progress()
    progress.begin_job("Scan")
    try:
        return _scan_and_publish(store, on_log, on_alert, progress)
    except Exception as exc:
        progress.log(f"Scan failed: {exc}", level="error")
        raise
    finally:
        progress.end_job()


def _scan_and_publish(
    store: ScannerStore,
    on_log: Callable[[str], None] | None,
    on_alert: AlertSink | None,
    progress: ScanProgress,
) -> int:
    settings = store.get_settings()
    snapshot = run_pipeline(settings, store=store)
    scan_id = store.save_snapshot(snapshot)
    if not snapshot.degraded:
        emit_alerts_for_snapshot(store, snapshot, on_alert)
    # Fast publish for the LTS dashboard; sweep backtests in a daemon thread.
    # Build coin rows (incl. chart closes + Vol Δ%) once — re-fetch on the BT pass was wiping sparklines.
    if _lts_enabled():
        try:
            from trendalgo.lts_vendor.bridge import opportunities_to_final_results
            from trendalgo.lts_vendor.public_snapshot import (
                load_public_snapshot,
                patch_scan_interval_seconds,
            )

            interval_sec = max(60, int(settings.interval_minutes) * 60)
            final_results = opportunities_to_final_results(snapshot)
            # Never wipe a populated Qualified list with an empty scan result.
            if not final_results:
                prev = load_public_snapshot()
                prev_coins = prev.get("coins") if isinstance(prev, dict) else None
                if isinstance(prev_coins, list) and len(prev_coins) > 0:
                    patch_scan_interval_seconds(interval_sec)
                    if on_log:
                        on_log(
                            "scanner: empty scan — kept prior LTS coins; "
                            f"interval set to {settings.interval_minutes}m"
                        )
                else:
                    progress.phase("Publish · LTS snapshot (empty)")
                    _publish_lts(snapshot, run_backtests=False, final_results=final_results)
                    if on_log:
                        on_log("scanner: LTS public snapshot published (empty)")
            else:
                progress.phase("Publish · LTS snapshot (backtests next)")
                _publish_lts(snapshot, run_backtests=False, final_results=final_results)
                if on_log:
                    on_log("scanner: LTS public snapshot published")
            if _backtest_enabled() and snapshot.opportunities and final_results:
                _start_backtest_job(snapshot, final_results, on_log, progress)
        except Exception as exc:
            progress.log(f"LTS snapshot failed: {exc}", level="error")
            if on_log:
                on_log(f"scanner: LTS public snapshot failed: {exc}")
    if on_log:
        status = "degraded" if snapshot.degraded else "live"
        on_log(f"scanner scan complete ({status}): {len(snapshot.opportunities)} opportunities")
    return scan_id


def _start_backtest_job(
    snapshot: QualifiedSnapshot,
    final_results: list[dict[str, Any]],
    on_log: Callable[[str], None] | None,
    progress: ScanProgress,
) -> None:
    progress.begin_job("Backtest")

    def _bt_job() -> None:
        try:
            _publish_lts(snapshot, run_backtests=True, final_results=final_results)
            if on_log:
                on_log("scanner: LTS backtest sweep merged into snapshot")
        except Exception as exc:
            progress.log(f"Backtest job failed: {exc}", level="error")
            if on_log:
                on_log(f"scanner: LTS backtest sweep failed: {exc}")
        finally:
            progress.end_job()

    try:
        threading.Thread(target=_bt_job, name="lts-backtest", daemon=True).start()
    except Exception:
        progress.end_job()
        raise


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
    minutes = max(60, int(settings.interval_minutes))
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: run_scheduled_scan(store, on_log, on_alert),
        "interval",
        minutes=minutes,
        id="trendalgo-scanner",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()
    if on_log:
        on_log(f"scanner scheduler started: every {minutes}m")
    return cast(object, scheduler)
