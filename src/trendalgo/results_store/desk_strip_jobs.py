"""Desk strip engine jobs: Secret Sauce Pan + refresh prices (AV-G-STR6/STR8)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import load_lts_rows
from trendalgo.results_store.desk_commands import ack_command
from trendalgo.results_store.desk_jobs import finish_run_scan
from trendalgo.results_store.store import ResultsStore

ScanFn = Callable[[Path, str], dict[str, Any]]
PublishFn = Callable[..., tuple[str, int]]
LiveFn = Callable[[Path, str, ScanFn | None], dict[str, Any]]


def _ok(
    cid: str, action: str, lane: str, status: str, *, rows: int = 0, run_id: str = ""
) -> dict[str, Any]:
    return {
        "id": cid,
        "action": action,
        "lane": lane,
        "status": status,
        "rows": rows,
        "run_id": run_id,
    }


def handle_run_sauce(
    root: Path, cid: str, action: str, lane: str, *, dry_run: bool
) -> dict[str, Any]:
    if dry_run:
        ack_command(root, cid, status="done", detail="acked:run_sauce")
        return _ok(cid, action, lane, "done")
    ack_command(root, cid, status="running")
    try:
        from trendalgo.device.opportunity_sauce_job import run_manual_sauce_pan

        rows = [r for r in load_lts_rows(root, lane=lane) if isinstance(r, dict)]
        out = run_manual_sauce_pan(root, rows, lane)
        ok = bool(out.get("ok"))
        detail = str(out.get("message") or ("sauce_ok" if ok else "sauce_empty"))[:200]
        symbols_raw = out.get("sauce_symbols")
        symbols: list[Any] = symbols_raw if isinstance(symbols_raw, list) else []
        store = ResultsStore(root)
        try:
            store.set_job_state(f"sauce:{lane}", "done" if ok else "empty")
        finally:
            store.close()
        ack_command(root, cid, status="done" if ok else "error", detail=detail)
        return _ok(cid, action, lane, "done" if ok else "error", rows=len(symbols))
    except Exception as exc:  # noqa: BLE001
        ack_command(root, cid, status="error", detail=str(exc)[:200])
        return _ok(cid, action, lane, "error")


def handle_refresh_prices(
    root: Path,
    cid: str,
    action: str,
    lane: str,
    *,
    dry_run: bool,
    batch_size: int,
    scan_fn: ScanFn | None,
    on_batch: Callable[[int], None] | None,
    run_live: LiveFn,
    publish: PublishFn,
) -> dict[str, Any]:
    """Clear OHLCV price caches then run a live desk scan (PySide Refresh prices)."""
    if not dry_run:
        try:
            from trendalgo.device.price_cache_clear import clear_price_caches

            clear_price_caches(root)
        except Exception:  # noqa: BLE001 — still attempt scan
            pass
    return finish_run_scan(
        root,
        cid,
        action,
        lane,
        dry_run=dry_run,
        force_fresh=False,
        batch_size=batch_size,
        scan_fn=scan_fn,
        on_batch=on_batch,
        run_live=run_live,
        publish=publish,
    )
