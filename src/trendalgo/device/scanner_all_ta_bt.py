"""All-TA pass-1 sweep for Opportunity scanner (fleet catalog → LTS Results shape)."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import needs_1m_base
from trendalgo.backtest.sim_accel import accel_backend
from trendalgo.device.scan_bt_prefs import (
    enabled_strategies,
    load_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_stake import DEFAULT_SCAN_EXCHANGE, DEVICE_SCAN_STAKE_USD
from trendalgo.device.scan_time_history import TimingSample, record_sample
from trendalgo.device.scanner_all_ta_coin import backtest_one_coin
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange, fleet_row_to_lts
from trendalgo.scanner.progress import get_scan_progress

__all__ = ["fleet_row_to_lts", "run_all_ta_scan_backtests"]


def _bt_workers() -> int:
    raw = os.environ.get("TRENDALGO_ALL_TA_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(8, int(raw)))
        except ValueError:
            pass
    return 4


def run_all_ta_scan_backtests(
    coins: list[dict[str, Any]],
    *,
    strategies: tuple[str, ...] | None = None,
    timeframes: tuple[str, ...] | None = None,
    prefs_root: Path | None = None,
) -> dict[str, Any] | None:
    """Catalog defaults + deepen — same keep rules as the Backtest tab."""
    if not coins:
        return None
    if os.environ.get("BACKTEST_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None

    from trendalgo.lts_vendor import install_import_shims

    install_import_shims()
    from trendalgo.lts_vendor.backtesting.data_loader import BacktestDataLoader
    from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings
    from trendalgo.lts_vendor.shims.database_cache import PriceCache

    rp = runner_params_from_settings()
    root = prefs_root or Path(rp.base_dir)
    prefs = load_scan_bt_prefs(root)
    strat_list = strategies or enabled_strategies(prefs.strategy_denylist)
    tf_list = timeframes or selected_timeframes(prefs)
    if not strat_list or not tf_list:
        return None
    stake = DEVICE_SCAN_STAKE_USD
    fee = fee_for_exchange(DEFAULT_SCAN_EXCHANGE, rp.backtest_fee_bps_round_trip)
    db_path = Path(rp.scanner_db_path)
    progress = get_scan_progress()
    subhour = needs_1m_base(tf_list)
    progress.log(
        f"All-TA stake=${stake:.0f} · fees={fee.exchange_id} "
        f"taker={fee.taker_pct * 100:.2f}% · accel={accel_backend()} · "
        f"{len(tf_list)} TFs · {len(strat_list)} strategies" + (" · 1m base" if subhour else "")
    )

    def loader_factory() -> Any:
        return BacktestDataLoader(
            cache=PriceCache(db_path),
            max_cache_age_hours=rp.cache_price_hours,
            loader_params=rp.loader,
        )

    progress.phase("Backtest (All TA)…", total=len(coins), unit="coins")
    started = time.perf_counter()
    tested = pruned = deepened = 0
    load_s = pass1_s = deepen_s = 0.0
    results: list[dict[str, Any]] = []
    per_coin: list[dict[str, Any]] = []
    workers = min(_bt_workers(), max(1, len(coins)))

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                backtest_one_coin,
                c,
                loader_factory=loader_factory,
                timeframes=tf_list,
                strat_list=strat_list,
                stake=stake,
                fee=fee,
                fee_bps_round_trip=rp.backtest_fee_bps_round_trip,
            ): c
            for c in coins
        }
        for fut in as_completed(futs):
            done += 1
            try:
                symbol, rows, stats = fut.result()
            except Exception as exc:
                progress.log(f"All-TA coin failed: {exc}", level="error")
                progress.step(done)
                continue
            results.extend(rows)
            tested += int(stats.get("tested", 0))
            pruned += int(stats.get("pruned", 0))
            deepened += int(stats.get("deepened", 0))
            load_s += float(stats.get("load_s", 0.0))
            pass1_s += float(stats.get("pass1_s", 0.0))
            deepen_s += float(stats.get("deepen_s", 0.0))
            elapsed_coin = float(stats.get("elapsed_s", 0))
            per_coin.append({"symbol": symbol, "elapsed_s": round(elapsed_coin, 3)})
            try:
                record_sample(
                    root,
                    TimingSample(
                        elapsed_s=elapsed_coin,
                        n_strategies=len(strat_list),
                        n_timeframes=len(tf_list),
                        had_subhour=subhour,
                        bars_base=int(stats.get("bars_base", 0) or 0),
                        ts=time.time(),
                    ),
                )
            except OSError:
                pass
            progress.step(done)

    elapsed = time.perf_counter() - started
    phase_s = {
        "ohlcv_load_s": round(load_s, 3),
        "pass1_defaults_s": round(pass1_s, 3),
        "deepen_s": round(deepen_s, 3),
    }
    progress.log(
        f"All-TA done: {len(results)} rows · tested={tested} pruned={pruned} "
        f"deepened={deepened} · {elapsed:.1f}s · load={phase_s['ohlcv_load_s']}s "
        f"pass1={phase_s['pass1_defaults_s']}s deepen={phase_s['deepen_s']}s"
    )
    return {
        "results": results,
        "coins_processed": len(coins),
        "rows_generated": len(results),
        "elapsed_s": round(elapsed, 3),
        "tested": tested,
        "pruned": pruned,
        "deepened": deepened,
        "phase_s": phase_s,
        "per_coin_s": per_coin,
    }
