"""Concurrent multi-desk scan orchestrator (Crypto + TradFi + Forex in parallel)."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from trendalgo.device.execution_log import append_execution_log
from trendalgo.device.scan_parallel import cpu_budget, set_coin_parallel
from trendalgo.results_store.desk_commands import ack_command

ScanFn = Callable[[Path, str], dict[str, Any]]
_ALL_LANES = ("crypto", "tradfi", "forex")


def _run_one_lane(
    root: Path,
    lane: str,
    *,
    dry_run: bool,
    force_fresh: bool,
    batch_size: int,
    run_live: Callable[[Path, str, ScanFn | None], dict[str, Any]],
    publish: Callable[..., tuple[str, int]],
    scan_fn: ScanFn | None,
) -> tuple[str, dict[str, Any]]:
    from trendalgo.results_store.desk_jobs import finish_run_scan  # noqa: PLC0415

    sub_cid = f"all-{lane}-{int(time.time())}"
    try:
        res = finish_run_scan(
            root,
            sub_cid,
            "run_scan",
            lane,
            dry_run=dry_run,
            force_fresh=force_fresh,
            batch_size=batch_size,
            scan_fn=scan_fn,
            on_batch=None,
            run_live=run_live,
            publish=publish,
        )
        return lane, res
    except Exception as exc:  # noqa: BLE001 — unconfigured TradFi/Forex keys skip cleanly
        return lane, {"lane": lane, "status": "skipped", "detail": str(exc)[:180], "rows": 0}


def run_all_desks_parallel(
    root: Path,
    cid: str,
    action: str,
    *,
    lanes: tuple[str, ...] = _ALL_LANES,
    dry_run: bool = False,
    force_fresh: bool = False,
    batch_size: int = 25,
    scan_fn: ScanFn | None = None,
    run_live: Callable[[Path, str, ScanFn | None], dict[str, Any]],
    publish: Callable[..., tuple[str, int]],
) -> dict[str, Any]:
    """Run all configured desks concurrently using independent per-lane locks/DBs."""
    ack_command(root, cid, status="running")
    t0 = time.perf_counter()
    active_lanes = tuple(dict.fromkeys(str(x).strip().lower() for x in lanes if str(x).strip()))
    per_lane_coins = max(1, cpu_budget() // max(1, len(active_lanes) * 3))
    set_coin_parallel(per_lane_coins)
    results: dict[str, dict[str, Any]] = {}
    try:
        with ThreadPoolExecutor(max_workers=max(1, len(active_lanes))) as pool:
            futs = [
                pool.submit(
                    _run_one_lane,
                    root,
                    ln,
                    dry_run=dry_run,
                    force_fresh=force_fresh,
                    batch_size=batch_size,
                    run_live=run_live,
                    publish=publish,
                    scan_fn=scan_fn,
                )
                for ln in active_lanes
            ]
            for fut in as_completed(futs):
                ln, res = fut.result()
                results[ln] = res
    finally:
        set_coin_parallel(1)

    total_rows = sum(int(r.get("rows") or 0) for r in results.values())
    elapsed = round(time.perf_counter() - t0, 3)
    ok_lanes = [ln for ln, r in results.items() if r.get("status") in {"done", "cancelled"}]
    detail = ", ".join(
        f"{ln}:{results[ln].get('status')}({results[ln].get('rows', 0)})" for ln in active_lanes
    )
    ack_command(root, cid, status="done" if ok_lanes or dry_run else "error", detail=detail[:200])
    append_execution_log(
        root,
        kind="scan_all",
        lane="all",
        total_s=elapsed,
        stages={ln: float(results[ln].get("rows") or 0) for ln in active_lanes},
        summary=f"Parallel 3-desk scan: {detail}",
    )
    return {
        "id": cid,
        "action": action,
        "lane": "all",
        "status": "done" if ok_lanes or dry_run else "error",
        "rows": total_rows,
        "run_id": "",
        "lanes": results,
    }
