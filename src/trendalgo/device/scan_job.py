"""Scan job (D-02): one Kraken USD spot scan on this PC, run in a worker. Public data only; no keys.

A plain function with no Qt. It returns plain values, and the window reads the saved scan from the
profile folder. After a live scan, pass-1 fleet backtests merge into LTS rows (Best BT / Results).
"""

from __future__ import annotations

import multiprocessing
import os
import time
from pathlib import Path
from typing import Any

from trendalgo.device.db import enable_wal
from trendalgo.device.lts_scan_model import build_lts_rows, save_lts_rows
from trendalgo.device.scan_model import ScanUnavailableError, device_scan_settings, scan_store_path
from trendalgo.device.scan_progress import ProgressReporter
from trendalgo.scanner import listings
from trendalgo.scanner.listings import DEFAULT_KRAKEN_SPOT
from trendalgo.scanner.pipeline import MarketFetcher, run_pipeline
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore

SCAN_LABEL = "Scan on this PC"


def scan_job(root: Path, fetcher: MarketFetcher | None = None) -> dict[str, Any]:
    """Run one scan and save it to this PC's scanner database. Returns the saved scan id and pair count.

    Raises ScanUnavailableError when Kraken's pair list or market data is missing. Nothing is saved
    then, so the scanner's synthetic fallback never reaches the database or the screen.
    """
    progress = get_scan_progress()
    progress.begin_job(SCAN_LABEL)
    reporter = ProgressReporter(root)
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    try:
        reporter.start()
        t = time.perf_counter()
        if tuple(listings.verify_kraken_listings()) == DEFAULT_KRAKEN_SPOT:
            raise ScanUnavailableError("the Kraken pair list was not available")
        timings["listings_s"] = round(time.perf_counter() - t, 3)
        t = time.perf_counter()
        try:
            snapshot = run_pipeline(device_scan_settings(root), fetcher=fetcher)
        except RuntimeError as exc:
            raise ScanUnavailableError(
                str(exc) or "the Kraken market data was not available"
            ) from exc
        timings["pipeline_s"] = round(time.perf_counter() - t, 3)
        if snapshot.degraded:
            raise ScanUnavailableError("the Kraken market data was not available")
        t = time.perf_counter()
        scan_id = _save(root, snapshot)
        timings["save_scan_s"] = round(time.perf_counter() - t, 3)
        # Live scans enrich charts + pass-1 BT; offline tests pass a fetcher and skip both.
        live = fetcher is None
        t = time.perf_counter()
        rows = build_lts_rows(snapshot, enrich_charts=live)
        timings["build_rows_s"] = round(time.perf_counter() - t, 3)
        bt_meta: dict[str, Any] = {}
        if live and rows:
            from trendalgo.device.lts_scan_model import coins_for_backtest, load_filters

            saved = load_filters(root)
            bt_candidates = coins_for_backtest(rows, saved)
            skipped = len(rows) - len(bt_candidates)
            if skipped:
                progress.log(
                    f"Pre-BT filters skip {skipped} of {len(rows)} coins "
                    "(volume / 7D / 30D / enrich floors)"
                )
            progress.log(f"Pass-1 backtest queue: {len(bt_candidates)} coins after filters")
            t = time.perf_counter()
            bt_rows, bt_meta = _merge_pass1_backtests(bt_candidates, root)
            timings["backtest_s"] = round(time.perf_counter() - t, 3)
            bt_meta["pre_bt_skipped"] = skipped
            by_sym = {str(c.get("symbol") or "").upper(): c for c in bt_rows}
            rows = [by_sym.get(str(c.get("symbol") or "").upper(), c) for c in rows]
        t = time.perf_counter()
        save_lts_rows(root, rows)
        timings["save_rows_s"] = round(time.perf_counter() - t, 3)
        timings["total_s"] = round(time.perf_counter() - t0, 3)
        return {
            "scan_id": scan_id,
            "pairs": len(snapshot.opportunities),
            "timings": timings,
            "backtest": bt_meta,
            "rows": len(rows),
        }
    finally:
        progress.end_job()
        reporter.stop()


def _merge_pass1_backtests(
    rows: list[dict[str, Any]], root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pass-1 backtest on every qualified coin; merge Best BT / Bot vs B&H / Results."""
    progress = get_scan_progress()
    meta: dict[str, Any] = {}
    # Nested ProcessPool inside the device WorkerPool often fails on Windows — stay single-worker.
    if multiprocessing.current_process().name != "MainProcess":
        os.environ["BACKTEST_PARALLEL_WORKERS"] = "1"
    try:
        from trendalgo.device.lts_scan_model import load_filters
        from trendalgo.device.scanner_signal_sets import (
            BT_SET_ALL_TA,
            normalize_bt_signal_set,
        )
        from trendalgo.lts_vendor.bridge import merge_backtest_into_coins, run_lts_backtest_sweep

        signal_set = normalize_bt_signal_set(load_filters(root).get("bt_signal_set"))
        meta["signal_set"] = signal_set
        progress.phase("Backtest…", total=len(rows), unit="coins")
        label = "All TA" if signal_set == BT_SET_ALL_TA else "3Commas"
        progress.log(f"Pass-1 backtest ({label}) on {len(rows)} qualified coins")
        t = time.perf_counter()
        if signal_set == BT_SET_ALL_TA:
            from trendalgo.device.scanner_all_ta_bt import run_all_ta_scan_backtests

            summary = run_all_ta_scan_backtests(rows)
        else:
            summary = run_lts_backtest_sweep(rows)
        meta["sweep_s"] = round(time.perf_counter() - t, 3)
        if isinstance(summary, dict):
            for key in ("elapsed_s", "tested", "pruned", "deepened", "rows_generated", "phase_s"):
                if key in summary:
                    meta[key] = summary[key]
        if summary is None:
            progress.log(
                "Backtest sweep returned no summary (check BACKTEST_ENABLED)",
                level="warn",
            )
            return _stamp_signal_set(rows, signal_set), meta
        t = time.perf_counter()
        merged = merge_backtest_into_coins(rows, summary)
        meta["merge_s"] = round(time.perf_counter() - t, 3)
        with_bt = sum(1 for c in merged if c.get("bot_best_net_pct") is not None)
        meta["coins_with_bt"] = with_bt
        progress.log(f"Backtest merge done: {with_bt}/{len(merged)} coins with Best BT")
        return _stamp_signal_set(merged, signal_set), meta
    except Exception as exc:
        progress.log(f"Backtest sweep failed: {exc}", level="error")
        meta["error"] = str(exc)
        return rows, meta


def _stamp_signal_set(rows: list[dict[str, Any]], signal_set: str) -> list[dict[str, Any]]:
    for coin in rows:
        coin["bt_signal_set"] = signal_set
    return rows


def _save(root: Path, snapshot: QualifiedSnapshot) -> int:
    path = scan_store_path(root)
    enable_wal(path)
    return ScannerStore(path).save_snapshot(snapshot)
