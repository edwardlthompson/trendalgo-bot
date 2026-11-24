"""Real-data 3-asset (Crypto + TradFi + Forex) full-pipeline benchmark for scan ETA calibration."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import needs_1m_base
from trendalgo.device.execution_log import append_execution_log
from trendalgo.device.pair_strategy_scan import SAUCE_PROGRESS_STEPS, scan_pair_strategies
from trendalgo.device.scan_bt_prefs import (
    enabled_strategies,
    load_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_stake import DEVICE_SCAN_STAKE_USD
from trendalgo.device.scan_time_history import (
    ScanTimeHistory,
    TimingSample,
    record_sample,
    save_history,
)
from trendalgo.device.scan_unit_timing import LAST_RUN_FILE
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange
from trendalgo.results_store.scan_settings_eta import scan_settings_eta

PROGRESS_FILE = "benchmark_progress.json"
RESULTS_FILE = "benchmark_last_results.json"
CANCEL_FLAG = "benchmark_cancel.flag"

_BENCHMARK_ASSETS = (
    ("Crypto", "BTC/USD", "BTC", "kraken"),
    ("TradFi", "AAPL/USD", "AAPL", "tradfi"),
    ("Forex", "EUR/USD", "EUR", "forex"),
)


def _write_progress(path: Path, payload: dict[str, Any]) -> None:
    """Best-effort atomic progress write; never raises on Windows file-share contention."""
    text = json.dumps(payload, separators=(",", ":"))
    tmp = path.with_suffix(".progress.tmp")
    for _ in range(3):
        try:
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(path)
            return
        except OSError:
            time.sleep(0.015)


def _write_results(path: Path, payload: dict[str, Any]) -> None:
    """Persist final benchmark results with retry + direct fallback."""
    text = json.dumps(payload, separators=(",", ":"))
    tmp = path.with_suffix(".results.tmp")
    for _ in range(10):
        try:
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(path)
            return
        except OSError:
            time.sleep(0.03)
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        pass


def _pick_top_strategy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    best_net = float("-inf")
    sauce_row: dict[str, Any] | None = None
    for r in rows:
        ind = str(r.get("indicator") or "")
        if "secret sauce" in ind.lower() and sauce_row is None:
            sauce_row = r
        if ind.startswith("Oracle") or ind.startswith("B&H"):
            continue
        raw_net = r.get("net_pct")
        try:
            net = float(raw_net) if raw_net is not None else float("-inf")
        except (TypeError, ValueError):
            continue
        if net > best_net:
            best_net = net
            best = r
    return {
        "top_indicator": str((best or {}).get("indicator") or "—"),
        "top_timeframe": str((best or {}).get("timeframe") or "—"),
        "top_net_pct": round(best_net, 2) if best is not None else None,
        "sauce_indicator": str((sauce_row or {}).get("indicator") or "—"),
        "sauce_net_pct": (
            round(float(sauce_row["net_pct"]), 2)
            if sauce_row and sauce_row.get("net_pct") is not None
            else None
        ),
    }


def _collect_asset_subtests(
    *,
    root: Path,
    asset_label: str,
    rows: list[dict[str, Any]],
    meta: dict[str, Any],
    src: str,
    bars_n: int,
    n_tf_default: int,
    load_s: float,
    pass1_s: float,
    deepen_s: float,
    mc_s: float,
    sauce_s: float,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    n_frames = int(meta.get("n_frames") or n_tf_default)
    tf_label = f"{n_frames} TFs"
    for pname, psec in (
        ("Data Fetch", load_s),
        ("Pass-1 Catalog", pass1_s),
        ("TSL Deepen", deepen_s),
        ("Market Context", mc_s),
        ("Secret Sauce", sauce_s),
    ):
        items.append(
            {
                "asset": asset_label,
                "component": pname,
                "timeframe": tf_label,
                "duration_s": round(psec, 3),
                "detail": f"src={src} · bars={bars_n} · rows={len(rows)}",
            }
        )

    bh_best: dict[str, Any] | None = None
    oracle_best: dict[str, Any] | None = None
    cat_best: dict[str, Any] | None = None
    sauce_rows: list[dict[str, Any]] = []
    for r in rows:
        ind = str(r.get("indicator") or "")
        net_v = r.get("net_pct")
        try:
            net_f = float(net_v) if net_v is not None else float("-inf")
        except (TypeError, ValueError):
            net_f = float("-inf")
        if ind == "B&H":
            if bh_best is None or net_f > float(bh_best.get("_net_f", float("-inf"))):
                bh_best = {**r, "_net_f": net_f}
        elif ind == "Oracle max":
            if oracle_best is None or net_f > float(oracle_best.get("_net_f", float("-inf"))):
                oracle_best = {**r, "_net_f": net_f}
        elif "secret sauce" in ind.lower():
            sauce_rows.append(r)
        elif cat_best is None or net_f > float(cat_best.get("_net_f", float("-inf"))):
            cat_best = {**r, "_net_f": net_f}

    def _add_outcome(label: str, row: dict[str, Any] | None) -> None:
        if row is None:
            return
        net_val = row.get("net_pct")
        net_str = f"{float(net_val):+.2f}%" if net_val is not None else "—"
        trades_str = str(row.get("trades") if row.get("trades") is not None else "—")
        items.append(
            {
                "asset": asset_label,
                "component": label,
                "timeframe": str(row.get("timeframe") or "—"),
                "duration_s": 0.0,
                "detail": f"net={net_str} · trades={trades_str} · {row.get('indicator')}",
            }
        )

    _add_outcome("Outcome: B&H", bh_best)
    _add_outcome("Outcome: Oracle max", oracle_best)
    _add_outcome("Outcome: Top Catalog", cat_best)
    for sr in sauce_rows[:6]:
        _add_outcome(f"Outcome: {sr.get('indicator')}", sr)

    last_path = root / LAST_RUN_FILE
    if last_path.exists():
        try:
            last_data = json.loads(last_path.read_text(encoding="utf-8"))
            for u in list(last_data.get("top_units") or [])[:8]:
                items.append(
                    {
                        "asset": asset_label,
                        "component": f"Slow unit: {u.get('strategy') or '—'}",
                        "timeframe": str(u.get("timeframe") or "—"),
                        "duration_s": round(float(u.get("elapsed_s") or 0.0), 3),
                        "detail": "Pass-1 strategy×TF unit",
                    }
                )
        except (OSError, ValueError, TypeError):
            pass
    return items


def run_quick_benchmark(root: Path) -> dict[str, Any]:
    """Run real-data full scans (including Secret Sauce) on 1 coin, 1 stock, and 1 FX pair."""
    root.mkdir(parents=True, exist_ok=True)
    cancel_path = root / CANCEL_FLAG
    if cancel_path.exists():
        cancel_path.unlink(missing_ok=True)

    prefs = load_scan_bt_prefs(root)
    strat_list = enabled_strategies(prefs.strategy_denylist) or ("RSI",)
    timeframes = selected_timeframes(prefs, root=root) or ("1h",)
    had_subhour = needs_1m_base(timeframes)
    per_asset_tests = max(1, len(timeframes) * len(strat_list)) + SAUCE_PROGRESS_STEPS
    grand_total = len(_BENCHMARK_ASSETS) * per_asset_tests

    from trendalgo.lts_vendor import install_import_shims

    install_import_shims()
    from trendalgo.lts_vendor.backtesting.data_loader import BacktestDataLoader
    from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings
    from trendalgo.lts_vendor.shims.database_cache import PriceCache

    rp = runner_params_from_settings()
    stake = DEVICE_SCAN_STAKE_USD
    loader = BacktestDataLoader(
        cache=PriceCache(Path(rp.scanner_db_path)),
        max_cache_age_hours=rp.cache_price_hours,
        loader_params=rp.loader,
    )

    t_start = time.perf_counter()
    completed_assets: list[dict[str, Any]] = []
    pending_samples: list[TimingSample] = []
    subtests: list[dict[str, Any]] = []
    cancelled = False

    state_lock = threading.Lock()
    latest_state: dict[str, Any] = {
        "running": True,
        "asset_index": 0,
        "assets_total": len(_BENCHMARK_ASSETS),
        "current_lane": "",
        "current_pair": "",
        "phase": "init",
        "tests_done": 0,
        "tests_total": grand_total,
        "tests_remaining": grand_total,
        "elapsed_s": 0.0,
        "message": "Starting 3-asset real-data benchmark…",
        "completed_assets": completed_assets,
    }
    stop_heartbeat = threading.Event()

    def _emit_progress(
        *,
        running: bool,
        asset_idx: int,
        lane_name: str,
        pair: str,
        phase: str,
        done_in_asset: int,
        message: str,
    ) -> None:
        done_total = min(grand_total, (asset_idx - 1) * per_asset_tests + max(0, done_in_asset))
        with state_lock:
            snap = {
                "running": running,
                "asset_index": asset_idx,
                "assets_total": len(_BENCHMARK_ASSETS),
                "current_lane": lane_name,
                "current_pair": pair,
                "phase": phase,
                "tests_done": done_total,
                "tests_total": grand_total,
                "tests_remaining": max(0, grand_total - done_total),
                "elapsed_s": round(time.perf_counter() - t_start, 2),
                "message": message,
                "completed_assets": list(completed_assets),
            }
            latest_state.clear()
            latest_state.update(snap)
        _write_progress(root / PROGRESS_FILE, snap)

    def _heartbeat_loop() -> None:
        while not stop_heartbeat.wait(0.5):
            with state_lock:
                snap = dict(latest_state)
                snap["elapsed_s"] = round(time.perf_counter() - t_start, 1)
                snap["completed_assets"] = list(completed_assets)
            _write_progress(root / PROGRESS_FILE, snap)

    hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    hb_thread.start()

    try:
        for idx, (lane_name, pair, sym, eid) in enumerate(_BENCHMARK_ASSETS, start=1):
            if cancel_path.exists():
                cancelled = True
                break
            lane_fee = fee_for_exchange(eid, rp.backtest_fee_bps_round_trip)
            _emit_progress(
                running=True,
                asset_idx=idx,
                lane_name=lane_name,
                pair=pair,
                phase="load",
                done_in_asset=0,
                message=f"[{idx}/3] Starting {lane_name} ({pair}) — fetching real data…",
            )
            t_asset = time.perf_counter()
            last_bars = 0

            def _on_prog(
                payload: dict[str, Any],
                _idx: int = idx,
                _ln: str = lane_name,
                _p: str = pair,
            ) -> None:
                nonlocal last_bars
                if cancel_path.exists():
                    raise InterruptedError("Benchmark cancelled by user")
                if payload.get("bars_base"):
                    last_bars = int(payload["bars_base"])
                d = int(payload.get("done") or 0)
                ph = str(payload.get("phase") or "scan")
                msg = str(payload.get("message") or "")
                _emit_progress(
                    running=True,
                    asset_idx=_idx,
                    lane_name=_ln,
                    pair=_p,
                    phase=ph,
                    done_in_asset=min(per_asset_tests, d),
                    message=f"[{_idx}/3] {_ln} ({_p}): {msg}",
                )

            try:
                rows, ctx = scan_pair_strategies(
                    symbol=sym,
                    pair=pair,
                    timeframes=timeframes,
                    strat_list=strat_list,
                    stake=stake,
                    fee=lane_fee,
                    loader=loader,
                    prefs_root=root,
                    on_progress=_on_prog,
                    include_sauce=True,
                    include_market_context=True,
                    exchange_id=eid,
                )
                asset_s = round(time.perf_counter() - t_asset, 3)
                meta = ctx if isinstance(ctx, dict) else {}
                raw_ps = meta.get("phase_s")
                phase_s: dict[str, Any] = raw_ps if isinstance(raw_ps, dict) else {}
                load_s = float(phase_s.get("load_s") or 0.0)
                pass1_s = float(phase_s.get("pass1_s") or 0.0)
                deepen_s = float(phase_s.get("deepen_s") or 0.0)
                mc_s = float(phase_s.get("mc_s") or 0.0)
                sauce_s = float(phase_s.get("sauce_s") or 0.0)
                src = str(meta.get("data_source") or eid)
                bars_n = int(meta.get("bars_base") or last_bars or 0)
                top = _pick_top_strategy(rows)
                status = "ok" if rows else "no_data"
                if rows and (pass1_s > 0 or load_s > 0):
                    pending_samples.append(
                        TimingSample(
                            elapsed_s=max(0.2, load_s + (pass1_s + deepen_s) * 1.20),
                            n_strategies=len(strat_list),
                            n_timeframes=len(timeframes),
                            had_subhour=had_subhour,
                            bars_base=bars_n,
                            ts=time.time(),
                            mc_s=mc_s,
                            sauce_s=sauce_s,
                            load_s=load_s,
                        )
                    )
                completed_assets.append(
                    {
                        "lane": lane_name,
                        "pair": pair,
                        "status": status,
                        "data_source": src,
                        "bars": bars_n,
                        "rows": len(rows),
                        "load_s": round(load_s, 3),
                        "pass1_s": round(pass1_s, 3),
                        "deepen_s": round(deepen_s, 3),
                        "mc_s": round(mc_s, 3),
                        "sauce_s": round(sauce_s, 3),
                        "total_s": asset_s,
                        **top,
                    }
                )
                subtests.extend(
                    _collect_asset_subtests(
                        root=root,
                        asset_label=f"{lane_name} ({pair})",
                        rows=rows,
                        meta=meta,
                        src=src,
                        bars_n=bars_n,
                        n_tf_default=len(timeframes),
                        load_s=load_s,
                        pass1_s=pass1_s,
                        deepen_s=deepen_s,
                        mc_s=mc_s,
                        sauce_s=sauce_s,
                    )
                )
            except InterruptedError:
                cancelled = True
                break
            except Exception as exc:  # noqa: BLE001
                asset_s = round(time.perf_counter() - t_asset, 3)
                err_msg = f"{type(exc).__name__}: {exc}"
                completed_assets.append(
                    {
                        "lane": lane_name,
                        "pair": pair,
                        "status": f"error: {err_msg[:80]}",
                        "data_source": eid,
                        "bars": 0,
                        "rows": 0,
                        "load_s": 0.0,
                        "pass1_s": 0.0,
                        "deepen_s": 0.0,
                        "mc_s": 0.0,
                        "sauce_s": 0.0,
                        "total_s": asset_s,
                        "top_indicator": "—",
                        "top_timeframe": "—",
                        "top_net_pct": None,
                        "sauce_indicator": "—",
                        "sauce_net_pct": None,
                    }
                )
                subtests.append(
                    {
                        "asset": f"{lane_name} ({pair})",
                        "component": "ERROR",
                        "timeframe": "—",
                        "duration_s": asset_s,
                        "detail": err_msg[:240],
                    }
                )
            _emit_progress(
                running=True,
                asset_idx=idx,
                lane_name=lane_name,
                pair=pair,
                phase="done",
                done_in_asset=per_asset_tests,
                message=f"[{idx}/3] Completed {lane_name} ({pair})",
            )
    finally:
        stop_heartbeat.set()
        hb_thread.join(timeout=1.0)

    if pending_samples and not cancelled:
        save_history(root, ScanTimeHistory())
        for smp in pending_samples:
            record_sample(root, smp)

    total_s = round(time.perf_counter() - t_start, 3)
    eta = scan_settings_eta(root, prefs=prefs)
    done_final = grand_total if not cancelled else len(completed_assets) * per_asset_tests
    report = {
        "ok": not cancelled,
        "cancelled": cancelled,
        "ran_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "benchmark_s": total_s,
        "tests_total": grand_total,
        "tests_done": done_final,
        "strategies_count": len(strat_list),
        "timeframes_count": len(timeframes),
        "assets": completed_assets,
        "subtests": subtests,
        "eta": eta,
    }
    _write_results(root / RESULTS_FILE, report)
    _write_progress(
        root / PROGRESS_FILE,
        {
            "running": False,
            "asset_index": len(completed_assets),
            "assets_total": len(_BENCHMARK_ASSETS),
            "current_lane": "Done",
            "current_pair": "",
            "phase": "cancelled" if cancelled else "done",
            "tests_done": done_final,
            "tests_total": grand_total,
            "tests_remaining": max(0, grand_total - done_final),
            "elapsed_s": total_s,
            "message": "Benchmark cancelled."
            if cancelled
            else f"Benchmark finished in {total_s:.1f}s.",
            "completed_assets": completed_assets,
        },
    )
    append_execution_log(
        root,
        kind="benchmark",
        lane="all",
        total_s=total_s,
        stages={
            "tests": float(grand_total),
            "strats": float(len(strat_list)),
            "tfs": float(len(timeframes)),
        },
        summary=f"Real 3-asset benchmark ({len(strat_list)} strats × {len(timeframes)} TFs + Sauce)",
    )
    return report
