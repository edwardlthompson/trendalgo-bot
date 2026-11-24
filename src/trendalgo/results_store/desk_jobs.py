"""Secondary desk strip jobs: DEX watch + backtest + scan execute (AV-G3/G4/G6)."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from trendalgo.device.execution_log import append_execution_log
from trendalgo.results_store.desk_commands import ack_command
from trendalgo.results_store.store import ResultsStore

ScanFn = Callable[[Path, str], dict[str, Any]]


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


def handle_pool_watch(
    root: Path, cid: str, action: str, lane: str, *, dry_run: bool
) -> dict[str, Any]:
    if dry_run:
        ack_command(root, cid, status="done", detail="acked:pool_watch")
        return _ok(cid, action, lane, "done")
    ack_command(root, cid, status="running")
    try:
        from trendalgo.device.dex_watch_scan_job import dex_watch_scan_job

        dex_watch_scan_job(root)
        ack_command(root, cid, status="done", detail="dex_watch")
        return _ok(cid, action, lane, "done")
    except Exception as exc:  # noqa: BLE001
        ack_command(root, cid, status="error", detail=str(exc)[:200])
        return _ok(cid, action, lane, "error")


def handle_share_board(root: Path, cid: str, action: str, lane: str) -> dict[str, Any]:
    ack_command(root, cid, status="running")
    try:
        from trendalgo.results_store.desk_share import share_board_png

        out = share_board_png(root, lane=lane)
        ack_command(root, cid, status="done", detail=str(out.get("path") or ""))
        return _ok(cid, action, lane, "done", rows=int(out.get("rows") or 0))
    except Exception as exc:  # noqa: BLE001
        ack_command(root, cid, status="error", detail=str(exc)[:200])
        return _ok(cid, action, lane, "error")


def run_pair_backtest_direct(root: Path, pair: str, lane: str = "crypto") -> dict[str, Any]:
    """Run single-pair All-TA scan directly (isolated from multi-desk scan queue)."""
    from trendalgo.device.last_pair_backtest import save_last_pair_backtest
    from trendalgo.device.pair_strategy_scan_job import pair_strategy_scan_job
    from trendalgo.device.results_view_prefs import load_results_prefs

    text = str(pair or "").strip().upper()
    if text and "/" not in text:
        text = f"{text}/USD"
    if not text or "/" not in text:
        text = load_results_prefs(root).last_pair or "BTC/USD"
    store = ResultsStore(root)
    try:
        store.set_job_state("backtest", "running", run_id=text)
        result = pair_strategy_scan_job(root, text)
        rows = [r for r in (result.get("rows") or []) if isinstance(r, dict)]
        ctx = result.get("market_context")
        market_context = ctx if isinstance(ctx, dict) else None
        if rows:
            save_last_pair_backtest(root, text, rows, market_context=market_context)
        run_id = store.start_run("all_ta", lane=lane, pair=text)
        if rows:
            store.append_strategy_rows(run_id, rows)
        store.finish_run(run_id, status="done")
        store.set_job_state("backtest", "done", run_id=run_id)
        elapsed = float(result.get("elapsed_s") or 0.0)
        append_execution_log(
            root,
            kind="backtest",
            lane=lane,
            pair=text,
            total_s=elapsed,
            stages=result.get("timings") if isinstance(result.get("timings"), dict) else None,
            summary=f"All-TA {text} · {len(rows)} strategies",
        )
        return {"ok": True, "pair": text, "rows": len(rows), "elapsed_s": elapsed, "run_id": run_id}
    except InterruptedError:
        store.set_job_state("backtest", "cancelled", run_id=text)
        return {"ok": False, "cancelled": True, "pair": text, "rows": 0}
    except Exception as exc:  # noqa: BLE001
        store.set_job_state("backtest", "error", run_id=text)
        return {"ok": False, "pair": text, "error": str(exc)[:240], "rows": 0}
    finally:
        store.close()


def handle_run_backtest(
    root: Path,
    cid: str,
    action: str,
    lane: str,
    *,
    dry_run: bool = False,
    params: dict[str, Any] | None = None,
    scan_job: Callable[[Path, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run All-TA pair scan (AV-G-OTH5) — no longer republishes stale JSON only."""
    from trendalgo.device.last_pair_backtest import save_last_pair_backtest
    from trendalgo.device.results_view_prefs import load_results_prefs

    raw = params if isinstance(params, dict) else {}
    pair = str(raw.get("pair") or "").strip().upper()
    if not pair or "/" not in pair:
        pair = load_results_prefs(root).last_pair or "BTC/USD"
    if dry_run:
        ack_command(root, cid, status="done", detail=f"acked:run_backtest:{pair}")
        return _ok(cid, action, lane, "done")

    ack_command(root, cid, status="running")
    store = ResultsStore(root)
    try:
        store.set_job_state("backtest", "running", run_id=cid)
        if scan_job is not None:
            result = scan_job(root, pair)
        else:
            from trendalgo.device.pair_strategy_scan_job import pair_strategy_scan_job

            result = pair_strategy_scan_job(root, pair)
        rows = [r for r in (result.get("rows") or []) if isinstance(r, dict)]
        ctx = result.get("market_context")
        market_context = ctx if isinstance(ctx, dict) else None
        if rows:
            save_last_pair_backtest(root, pair, rows, market_context=market_context)
        run_id = store.start_run("all_ta", lane=lane, pair=pair)
        if rows:
            store.append_strategy_rows(run_id, rows)
        store.finish_run(run_id, status="done")
        store.set_job_state("backtest", "done", run_id=run_id)
        elapsed = float(result.get("elapsed_s") or 0.0)
        append_execution_log(
            root,
            kind="backtest",
            lane=lane,
            pair=pair,
            total_s=elapsed,
            stages=result.get("timings") if isinstance(result.get("timings"), dict) else None,
            summary=f"All-TA {pair} · {len(rows)} strategies",
        )
        ack_command(
            root,
            cid,
            status="done",
            detail=f"all_ta:{pair}:rows={len(rows)}:elapsed={result.get('elapsed_s')}",
        )
        return _ok(cid, action, lane, "done", rows=len(rows), run_id=run_id)
    except Exception as exc:  # noqa: BLE001 — desk worker must ack
        store.set_job_state("backtest", "error", run_id=cid)
        ack_command(root, cid, status="error", detail=str(exc)[:200])
        return _ok(cid, action, lane, "error")
    finally:
        store.close()


def alert_scan_done(root: Path, lane: str, written: int) -> None:
    try:
        from trendalgo.device.scanner_alerts_store import append_log_alert

        append_log_alert(
            root, kind="scan_log", reason=f"{lane} scan done · {written} board rows", pair=""
        )
    except Exception:  # noqa: BLE001 — alerts must not fail the desk job
        pass


def finish_run_scan(
    root: Path,
    cid: str,
    action: str,
    lane: str,
    *,
    dry_run: bool,
    force_fresh: bool,
    batch_size: int,
    scan_fn: ScanFn | None,
    on_batch: Callable[[int], None] | None,
    run_live: Callable[[Path, str, ScanFn | None], dict[str, Any]],
    publish: Callable[..., tuple[str, int]],
) -> dict[str, Any]:
    ack_command(root, cid, status="running")
    store = ResultsStore(root)
    t0 = time.perf_counter()
    live_res: dict[str, Any] = {}
    try:
        run_id = store.start_run(
            "lane_scan", lane=lane, params={"dry_run": dry_run, "force_fresh": force_fresh}
        )
        store.set_job_state(f"scan:{lane}", "running", run_id=run_id)
        if not dry_run:
            try:
                res = run_live(root, lane, scan_fn)
                if isinstance(res, dict):
                    live_res = res
            except Exception as exc:  # noqa: BLE001
                store.finish_run(run_id, status="error")
                store.set_job_state(f"scan:{lane}", "error", run_id=run_id)
                ack_command(root, cid, status="error", detail=str(exc)[:200])
                return _ok(cid, action, lane, "error", run_id=run_id)
        t_pub = time.perf_counter()
        status, written = publish(
            store, root, lane=lane, run_id=run_id, batch_size=batch_size, on_batch=on_batch
        )
        pub_s = round(time.perf_counter() - t_pub, 3)
        if status == "done":
            stages = (
                dict(live_res.get("timings") or {})
                if isinstance(live_res.get("timings"), dict)
                else {}
            )
            if dry_run:
                alert_scan_done(root, lane, written)
            else:
                t_al = time.perf_counter()
                try:
                    from trendalgo.device.desk_scan_alerts import emit_desk_scan_alerts

                    emit_desk_scan_alerts(root, lane=lane)
                except Exception:  # noqa: BLE001 — alerts must not fail the desk job
                    alert_scan_done(root, lane, written)
                stages["alerts_s"] = round(time.perf_counter() - t_al, 3)
            stages["publish_s"] = pub_s
            append_execution_log(
                root,
                kind="scan",
                lane=lane,
                total_s=round(time.perf_counter() - t0, 3),
                stages=stages,
                summary=f"{lane} scan {status} · {written} rows",
            )
        ack_command(root, cid, status=status, detail=f"rows={written}")
        return _ok(cid, action, lane, status, rows=written, run_id=run_id)
    finally:
        store.close()
