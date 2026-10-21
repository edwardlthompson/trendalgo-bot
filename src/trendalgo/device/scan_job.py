"""Scan job (D-02): multi-venue spot scan on this PC (keyed exchanges).

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
from trendalgo.device.lts_scan_model import build_lts_rows, load_filters, save_lts_rows
from trendalgo.device.scan_identity import row_key
from trendalgo.device.scan_model import ScanUnavailableError, device_scan_settings, scan_store_path
from trendalgo.device.scan_progress import ProgressReporter
from trendalgo.device.scan_venues import resolve_scan_exchange_ids
from trendalgo.device.secrets_vault import VaultSecretStore
from trendalgo.exchanges.private_client import ccxt_client, set_secret_store
from trendalgo.exchanges.registry import load_registry
from trendalgo.scanner.pipeline import MarketFetcher, run_pipeline
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore
from trendalgo.scanner.venue_market import run_venue_pipeline

SCAN_LABEL = "Scan on this PC"


def scan_job(root: Path, fetcher: MarketFetcher | None = None) -> dict[str, Any]:
    """Run scans for selected keyed venues and save merged Qualified rows."""
    progress = get_scan_progress()
    progress.begin_job(SCAN_LABEL)
    reporter = ProgressReporter(root)
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    try:
        reporter.start()
        settings = device_scan_settings(root)
        saved = load_filters(root)
        vault = VaultSecretStore()
        vault.bind_registry()
        set_secret_store(vault)

        # Offline tests: single Kraken pipeline with injected fetcher.
        if fetcher is not None:
            from trendalgo.scanner import listings
            from trendalgo.scanner.listings import DEFAULT_KRAKEN_SPOT

            if tuple(listings.verify_kraken_listings()) == DEFAULT_KRAKEN_SPOT:
                raise ScanUnavailableError("the Kraken pair list was not available")
            try:
                snapshot = run_pipeline(settings, fetcher=fetcher)
            except RuntimeError as exc:
                raise ScanUnavailableError(
                    str(exc) or "the Kraken market data was not available"
                ) from exc
            if snapshot.degraded:
                raise ScanUnavailableError("the Kraken market data was not available")
            rows = build_lts_rows(snapshot, enrich_charts=False, exchange_id="kraken")
            scan_id = _save(root, snapshot)
            save_lts_rows(root, rows)
            return {
                "scan_id": scan_id,
                "pairs": len(snapshot.opportunities),
                "timings": {"total_s": round(time.perf_counter() - t0, 3)},
                "backtest": {},
                "rows": len(rows),
            }

        venues = resolve_scan_exchange_ids(saved, store=vault)
        if not venues:
            raise ScanUnavailableError(
                "no exchanges selected — save API keys in Settings and check venues to scan"
            )

        all_rows: list[dict[str, Any]] = []
        last_snap: QualifiedSnapshot | None = None
        registry = load_registry()
        for eid in venues:
            entry = registry.by_id(eid)
            if entry is None:
                progress.log(f"Venue {eid}: unknown registry id", level="warn")
                continue
            if vault.read_entry(eid) is None:
                progress.log(f"Venue {eid}: no API key — skipped", level="warn")
                continue
            t = time.perf_counter()
            try:
                client = ccxt_client(entry, store=vault)
                snap = run_venue_pipeline(settings, entry, client=client)
            except Exception as exc:
                progress.log(f"Venue {eid}: failed ({exc})", level="error")
                continue
            timings[f"pipeline_{eid}_s"] = round(time.perf_counter() - t, 3)
            last_snap = snap
            t = time.perf_counter()
            # Chart enrich still hits public OHLCV; keep False for non-Kraken speed/safety,
            # True only for kraken to preserve prior spark behavior when possible.
            enrich = eid == "kraken"
            venue_rows = build_lts_rows(snap, enrich_charts=enrich, exchange_id=eid)
            timings[f"build_{eid}_s"] = round(time.perf_counter() - t, 3)
            all_rows.extend(venue_rows)

        if not all_rows:
            raise ScanUnavailableError("no venues returned qualified pairs")

        assert last_snap is not None
        t = time.perf_counter()
        scan_id = _save(root, last_snap)
        timings["save_scan_s"] = round(time.perf_counter() - t, 3)

        bt_meta: dict[str, Any] = {}
        from trendalgo.device.lts_scan_model import coins_for_backtest

        bt_candidates = coins_for_backtest(all_rows, saved)
        skipped = len(all_rows) - len(bt_candidates)
        if skipped:
            progress.log(
                f"Pre-BT volume floor skips {skipped} of {len(all_rows)} coins "
                "(column gain filters do not skip BT)"
            )
        progress.log(f"Pass-1 backtest queue: {len(bt_candidates)} qualified coins")
        t = time.perf_counter()
        bt_rows, bt_meta = _merge_pass1_backtests(bt_candidates, root)
        timings["backtest_s"] = round(time.perf_counter() - t, 3)
        bt_meta["pre_bt_skipped"] = skipped
        by_key = {row_key(c): c for c in bt_rows}
        rows = [by_key.get(row_key(c), c) for c in all_rows]
        t = time.perf_counter()
        save_lts_rows(root, rows)
        timings["save_rows_s"] = round(time.perf_counter() - t, 3)
        timings["total_s"] = round(time.perf_counter() - t0, 3)
        return {
            "scan_id": scan_id,
            "pairs": len(rows),
            "timings": timings,
            "backtest": bt_meta,
            "rows": len(rows),
            "venues": venues,
        }
    finally:
        set_secret_store(None)
        progress.end_job()
        reporter.stop()


def _merge_pass1_backtests(
    rows: list[dict[str, Any]], root: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pass-1 backtest on every qualified coin; merge Best BT / Bot vs B&H / Results."""
    progress = get_scan_progress()
    meta: dict[str, Any] = {}
    if multiprocessing.current_process().name != "MainProcess":
        os.environ["BACKTEST_PARALLEL_WORKERS"] = "1"
    try:
        from trendalgo.device.scan_bt_prefs import load_scan_bt_prefs
        from trendalgo.device.scanner_signal_sets import (
            BT_SET_ALL_TA,
            normalize_bt_signal_set,
        )
        from trendalgo.lts_vendor.bridge import merge_backtest_into_coins, run_lts_backtest_sweep

        signal_set = normalize_bt_signal_set(load_scan_bt_prefs(root).bt_signal_set)
        meta["signal_set"] = signal_set
        progress.phase("Backtest…", total=len(rows), unit="coins")
        label = "All TA" if signal_set == BT_SET_ALL_TA else "3Commas"
        progress.log(f"Pass-1 backtest ({label}) on {len(rows)} qualified coins")
        t = time.perf_counter()
        if signal_set == BT_SET_ALL_TA:
            from trendalgo.device.scanner_all_ta_bt import run_all_ta_scan_backtests

            summary = run_all_ta_scan_backtests(rows, prefs_root=root)
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
