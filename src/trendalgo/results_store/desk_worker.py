"""Process Avalonia desk_commands → lane scan + progressive results.db (AV-G3)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import load_lts_rows
from trendalgo.results_store.desk_commands import ack_command, peek_pending
from trendalgo.results_store.desk_jobs import (
    finish_run_scan,
    handle_pool_watch,
    handle_run_backtest,
    handle_share_board,
)
from trendalgo.results_store.desk_strip_jobs import handle_refresh_prices, handle_run_sauce
from trendalgo.results_store.store import ResultsStore

ScanFn = Callable[[Path, str], dict[str, Any]]


def _cancel_path(root: Path, lane: str) -> Path:
    return root / f"desk_cancel_{lane}.flag"


def request_cancel(root: Path, lane: str) -> None:
    key = str(lane or "crypto").strip().lower() or "crypto"
    _cancel_path(root, key).write_text("1", encoding="utf-8")
    store = ResultsStore(root)
    try:
        store.set_job_state(f"scan:{key}", "cancelled")
    finally:
        store.close()


def clear_cancel(root: Path, lane: str) -> None:
    _cancel_path(root, str(lane or "crypto").strip().lower() or "crypto").unlink(missing_ok=True)


def is_cancel_requested(root: Path, lane: str) -> bool:
    return _cancel_path(root, str(lane or "crypto").strip().lower() or "crypto").is_file()


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


def _publish_batches(
    store: ResultsStore,
    root: Path,
    *,
    lane: str,
    run_id: str,
    batch_size: int,
    on_batch: Callable[[int], None] | None = None,
) -> tuple[str, int]:
    rows = [r for r in load_lts_rows(root, lane=lane) if isinstance(r, dict)]
    written, total = 0, len(rows)
    for i in range(0, total, max(1, batch_size)):
        if is_cancel_requested(root, lane):
            store.finish_run(run_id, status="cancelled")
            store.set_job_state(f"scan:{lane}", "cancelled", run_id=run_id)
            return "cancelled", written
        chunk = rows[i : i + batch_size]
        store.append_opportunity_rows(run_id, chunk, start_id=written)
        written += len(chunk)
        store.set_job_state(f"scan:{lane}", f"running:{written}/{total}", run_id=run_id)
        if on_batch is not None:
            on_batch(written)
    store.finish_run(run_id, status="done")
    store.set_job_state(f"scan:{lane}", "done", run_id=run_id)
    return "done", written


def _run_live_scan(root: Path, lane: str, scan_fn: ScanFn | None) -> dict[str, Any]:
    if scan_fn is not None:
        return scan_fn(root, lane)
    if lane in {"tradfi", "forex"}:
        from trendalgo.device.lane_scan_job import lane_scan_job

        return lane_scan_job(root, lane)  # type: ignore[arg-type]
    from trendalgo.device.scan_job import scan_job

    return scan_job(root)


def process_pending(
    root: Path,
    *,
    dry_run: bool = False,
    batch_size: int = 25,
    scan_fn: ScanFn | None = None,
    on_batch: Callable[[int], None] | None = None,
) -> dict[str, Any] | None:
    cmd = peek_pending(root)
    if cmd is None:
        return None
    cid, action = str(cmd["id"]), str(cmd.get("action") or "")
    lane = str(cmd.get("lane") or "crypto").strip().lower() or "crypto"
    if action == "cancel_scan":
        request_cancel(root, lane)
        ack_command(root, cid, status="done", detail="cancel signaled")
        return _ok(cid, action, lane, "done")
    if action == "pool_watch":
        return handle_pool_watch(root, cid, action, lane, dry_run=dry_run)
    if action == "run_sauce":
        return handle_run_sauce(root, cid, action, lane, dry_run=dry_run)
    if action == "refresh_prices":
        return handle_refresh_prices(
            root,
            cid,
            action,
            lane,
            dry_run=dry_run,
            batch_size=batch_size,
            scan_fn=scan_fn,
            on_batch=on_batch,
            run_live=_run_live_scan,
            publish=_publish_batches,
        )
    if action == "run_backtest":
        raw_params = cmd.get("params")
        bt_params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
        return handle_run_backtest(root, cid, action, lane, dry_run=dry_run, params=bt_params)
    if action == "share_board":
        return handle_share_board(root, cid, action, lane)
    if action == "run_all_scans":
        from trendalgo.results_store.multi_desk_scan import run_all_desks_parallel

        raw_params = cmd.get("params")
        params = raw_params if isinstance(raw_params, dict) else {}
        raw_lanes = params.get("lanes")
        valid = ("crypto", "tradfi", "forex")
        chosen_lanes = (
            tuple(
                str(x).strip().lower()
                for x in (raw_lanes if isinstance(raw_lanes, list) else [])
                if str(x).strip().lower() in valid
            )
            or valid
        )
        return run_all_desks_parallel(
            root,
            cid,
            action,
            lanes=chosen_lanes,
            dry_run=dry_run,
            force_fresh=bool(params.get("force_fresh")),
            batch_size=batch_size,
            scan_fn=scan_fn,
            run_live=_run_live_scan,
            publish=_publish_batches,
        )
    if action != "run_scan":
        ack_command(root, cid, status="done", detail=f"acked:{action}")
        return _ok(cid, action, lane, "done")
    clear_cancel(root, lane)
    raw_scan_params = cmd.get("params")
    scan_params: dict[str, Any] = raw_scan_params if isinstance(raw_scan_params, dict) else {}
    force_fresh = bool(scan_params.get("force_fresh"))
    if force_fresh and not dry_run:
        from trendalgo.results_store.desk_more import apply_force_fresh

        apply_force_fresh(root)
    return finish_run_scan(
        root,
        cid,
        action,
        lane,
        dry_run=dry_run,
        force_fresh=force_fresh,
        batch_size=batch_size,
        scan_fn=scan_fn,
        on_batch=on_batch,
        run_live=_run_live_scan,
        publish=_publish_batches,
    )


def drain_pending(
    root: Path,
    *,
    dry_run: bool = False,
    batch_size: int = 25,
    scan_fn: ScanFn | None = None,
    on_batch: Callable[[int], None] | None = None,
) -> dict[str, Any] | None:
    """Process every pending command in queue order; returns the last result."""
    last: dict[str, Any] | None = None
    while True:
        res = process_pending(
            root,
            dry_run=dry_run,
            batch_size=batch_size,
            scan_fn=scan_fn,
            on_batch=on_batch,
        )
        if res is None:
            return last
        last = res
