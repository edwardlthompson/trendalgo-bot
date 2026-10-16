"""`--selftest` for the device app: workers (D1, D2), WAL and the lock (D3), TA-Lib, the scan
(D-02), and the window.

Each check prints OK or FAIL. The exit code is 0 only when every check passes. The frozen build runs
the same checks, so a passing exit proves the packaged app works outside the source tree.
"""

from __future__ import annotations

import importlib
import math
import multiprocessing
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from trendalgo.device.context import open_context
from trendalgo.device.db import enable_wal
from trendalgo.device.jobs import engine_check_job
from trendalgo.device.lock import ProfileBusyError, ProfileLock
from trendalgo.device.scan_job import scan_job
from trendalgo.device.scan_offline import offline_listings, offline_market
from trendalgo.device.workers import WorkerPool
from trendalgo.lts_vendor.backtesting.signals import talib_available

WORKERS = 2
RESULT_TIMEOUT_S = 120.0
_QT_HOLDER: list[Any] = []  # keeps a QApplication this check created alive for the process


def run_selftest(*, include_window: bool = True) -> int:
    checks: dict[str, Callable[[], None]] = {
        "workers": check_workers,
        "wal": check_wal,
        "lock": check_lock,
        "talib": check_talib,
        "pandas_ta": check_pandas_ta,
        "glossary": check_glossary,
        "scan": check_scan,
        "charts": check_charts,
        "portfolio": check_portfolio,
        "host_client": check_host_client,
    }
    if include_window:
        checks["window"] = check_window
    failures = 0
    for name, check in checks.items():
        try:
            check()
        except Exception as exc:  # the report names the failed check; no trace is printed
            failures += 1
            print(f"FAIL {name}: {exc}")
        else:
            print(f"OK {name}")
    return 1 if failures else 0


def check_workers() -> None:
    pool = WorkerPool(WORKERS)
    try:
        pending = [pool.submit(engine_check_job, seed) for seed in range(WORKERS)]
        for result in pending:
            summary = result.get(timeout=RESULT_TIMEOUT_S)
            if not math.isfinite(float(summary["final_equity"])):
                raise RuntimeError("a worker returned a non-finite equity")
    finally:
        pool.shutdown()
    if multiprocessing.active_children():
        raise RuntimeError("a worker process is still running after shutdown")


def check_wal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mode = enable_wal(Path(tmp) / "selftest.db")
    if mode != "wal":
        raise RuntimeError(f"journal mode is {mode}, expected wal")


def check_talib() -> None:
    """The device ships TA-Lib. Without it, RSI, MACD, and Bollinger signals fall back to pandas."""
    if talib_available():
        return
    try:
        importlib.import_module("talib")  # signals.py hides the error; re-import to name it
    except Exception as exc:  # the report names the cause; no trace is printed
        raise RuntimeError(f"TA-Lib did not import: {exc}") from exc
    raise RuntimeError("TA-Lib imports, but the signal code does not use it")


def check_pandas_ta() -> None:
    """All-TA backtests need pandas-ta-classic for ~85 catalog indicators."""
    from trendalgo.ta.pandas_ta_catalog import pandas_ta_available

    if not pandas_ta_available():
        raise RuntimeError("pandas-ta-classic did not import")


def check_glossary() -> None:
    """Bundled glossary JSON must ship with the frozen app (indicator clicks + Glossary tab)."""
    from trendalgo.device.glossary_model import (
        bundled_glossary_path,
        clear_glossary_cache,
        load_glossary,
    )

    clear_glossary_cache()
    path = bundled_glossary_path()
    if not path.is_file():
        raise RuntimeError(f"glossary file missing: {path}")
    entries, error = load_glossary()
    if error:
        raise RuntimeError(error)
    if len(entries) < 100:
        raise RuntimeError(f"glossary too small: {len(entries)} entries")


def check_scan() -> None:
    """One scan through the real job and store, with a fixed market and no Kraken call. Importing ccxt
    proves the live pair-list library is bundled, so a frozen build cannot silently lack it."""
    importlib.import_module("ccxt")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp, offline_listings():
        result = scan_job(Path(tmp) / "profile", fetcher=offline_market)
    if int(result["scan_id"]) < 1:
        raise RuntimeError("the scan saved no snapshot")


def check_charts() -> None:
    """QtCharts must import so the Portfolio equity curve works in a frozen build."""
    importlib.import_module("PySide6.QtCharts")


def check_portfolio() -> None:
    """Read-only portfolio open: missing file stays missing; a seeded file loads."""
    from trendalgo.device.portfolio_model import load_overview
    from trendalgo.portfolio.db import HoldingRow, PortfolioStore

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        missing = Path(tmp) / "missing.db"
        try:
            PortfolioStore(missing, create=False)
        except FileNotFoundError:
            pass
        else:
            raise RuntimeError("create=False opened a missing portfolio file")
        if missing.exists():
            raise RuntimeError("create=False created a portfolio file")
        path = Path(tmp) / "portfolio.db"
        store = PortfolioStore(path, create=True)
        account = store.get_or_create_account("kraken", "default")
        store.insert_snapshot(
            account,
            total_usd=100.0,
            holdings=[HoldingRow("BTC", 0.001, 100_000.0, 100.0, cost_basis_usd=90.0)],
            source="selftest",
        )
        overview = load_overview(path)
        if overview is None or overview.net_worth_usd != 100.0:
            raise RuntimeError("portfolio overview did not load")


def check_host_client() -> None:
    """Import the shared HostClient and refuse a non-loopback URL without a pin."""
    from trendalgo.device.host_client import HostClient, HostRefusedError

    try:
        HostClient("https://example.invalid", "owner-1", "secret", cert_sha256="")
    except HostRefusedError:
        return
    raise RuntimeError("HostClient accepted a remote URL without a certificate pin")


def check_lock() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "device.lock"
        with ProfileLock(path):
            rival = ProfileLock(path)
            try:
                rival.acquire()
            except ProfileBusyError:
                return
            rival.release()
    raise RuntimeError("a second window was allowed on the same profile")


def check_window() -> None:
    """Build the real main window offscreen. In a frozen build this proves the Qt plugins load."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from trendalgo.device.views.main_window import MainWindow

    if QApplication.instance() is None:
        _QT_HOLDER.append(QApplication([]))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        ctx = open_context(Path(tmp) / "profile")
        pool = WorkerPool(1)
        try:
            window = MainWindow(ctx, pool)
            window.close()
        finally:
            pool.shutdown()
