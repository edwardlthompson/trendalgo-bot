"""All-TA pass-1 sweep for Opportunity scanner (fleet catalog → LTS Results shape)."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import needs_1m_base
from trendalgo.device.opportunity_sauce import (
    OPPORTUNITY_SAUCE_TOP_N,
    mark_sauce_ever,
    oracle_rank_score,
    select_sauce_symbols,
)
from trendalgo.device.scan_bt_prefs import (
    enabled_strategies,
    load_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_parallel import (
    all_ta_coin_workers,
    parallel_log_bits,
    set_coin_parallel,
)
from trendalgo.device.scan_stake import DEFAULT_SCAN_EXCHANGE, DEVICE_SCAN_STAKE_USD
from trendalgo.device.scan_time_history import TimingSample, record_sample
from trendalgo.device.scanner_all_ta_pool import run_opportunity_sauce_pass, run_pool
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange, fleet_row_to_lts
from trendalgo.device.sim_accel_label import catalog_accel_label
from trendalgo.scanner.progress import get_scan_progress

# Compat alias for tests that patch ``mod._run_pool``.
_run_pool = run_pool


def _sauce_pool_on_seeds(
    sauce_coins: list[dict[str, Any]],
    *,
    loader_factory: Any,
    timeframes: tuple[str, ...],
    strat_list: tuple[str, ...],
    stake: float,
    fee: Any,
    fee_bps: float,
    prefs_root: Path,
    progress: Any,
    seed_rows_by_symbol: dict[str, list[dict[str, Any]]],
    on_ok: Any,
    on_ctx: Any,
) -> bool:
    """Serial Sauce-only via ``_run_pool`` (patchable in tests)."""
    if not sauce_coins:
        return False
    set_coin_parallel(1)
    progress.phase("Backtest (Secret Sauce)…", total=len(sauce_coins), unit="coins")
    progress.log(
        f"Sauce pass: {len(sauce_coins)} coins · sauce-only · {parallel_log_bits()} (serial)"
    )
    _run_pool(
        sauce_coins,
        workers=1,
        include_sauce=True,
        loader_factory=loader_factory,
        timeframes=timeframes,
        strat_list=strat_list,
        stake=stake,
        fee=fee,
        fee_bps=fee_bps,
        prefs_root=prefs_root,
        progress=progress,
        on_ok=on_ok,
        on_ctx=on_ctx,
        on_score=None,
        seed_rows_by_symbol=seed_rows_by_symbol,
    )
    return True


__all__ = [
    "all_ta_coin_workers",
    "fleet_row_to_lts",
    "run_all_ta_scan_backtests",
    "run_opportunity_sauce_pass",
]


def run_all_ta_scan_backtests(
    coins: list[dict[str, Any]],
    *,
    strategies: tuple[str, ...] | None = None,
    timeframes: tuple[str, ...] | None = None,
    prefs_root: Path | None = None,
) -> dict[str, Any] | None:
    """Catalog+deepen all coins; Sauce Lab only when sauce_with_scan (top-N)."""
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
    workers = min(all_ta_coin_workers(), max(1, len(coins)))
    set_coin_parallel(workers)
    sauce_top_n = int(
        getattr(prefs, "sauce_top_n", OPPORTUNITY_SAUCE_TOP_N) or OPPORTUNITY_SAUCE_TOP_N
    )
    sauce_with = bool(getattr(prefs, "sauce_with_scan", True))
    mc_with = bool(getattr(prefs, "market_context_with_scan", True))
    sauce_note = f"Sauce top {sauce_top_n}" if sauce_with else "Sauce off"
    mc_note = "MC on" if mc_with else "MC off"
    progress.log(
        f"All-TA stake=${stake:.0f} · fees={fee.exchange_id} "
        f"taker={fee.taker_pct * 100:.2f}% · {catalog_accel_label()} · "
        f"{parallel_log_bits()} · "
        f"{len(tf_list)} TFs · {len(strat_list)} strategies · "
        f"{sauce_note} · {mc_note}" + (" · 1m base" if subhour else "")
    )

    def loader_factory() -> Any:
        return BacktestDataLoader(
            cache=PriceCache(db_path),
            max_cache_age_hours=rp.cache_price_hours,
            loader_params=rp.loader,
        )

    started = time.perf_counter()
    tested = pruned = deepened = 0
    load_s = pass1_s = deepen_s = 0.0
    per_coin: list[dict[str, Any]] = []
    market_contexts: dict[str, dict[str, Any]] = {}
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    scored: list[tuple[str, float]] = []
    sauce_syms: list[str] = []
    coin_by_sym = {
        str(c.get("symbol") or "").strip().upper(): c
        for c in coins
        if str(c.get("symbol") or "").strip()
    }

    def _accumulate(
        symbol: str,
        rows: list[dict[str, Any]],
        stats: dict[str, float],
        *,
        tally: bool,
        label: str,
    ) -> None:
        nonlocal tested, pruned, deepened, load_s, pass1_s, deepen_s
        by_symbol[symbol] = list(rows)
        if tally:
            tested += int(stats.get("tested", 0))
            pruned += int(stats.get("pruned", 0))
            deepened += int(stats.get("deepened", 0))
            load_s += float(stats.get("load_s", 0.0))
            pass1_s += float(stats.get("pass1_s", 0.0))
            deepen_s += float(stats.get("deepen_s", 0.0))
        elapsed_coin = float(stats.get("elapsed_s", 0))
        per_coin.append({"symbol": symbol, "elapsed_s": round(elapsed_coin, 3), "phase": label})
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
                    mc_s=float(stats.get("mc_s", 0.0) or 0.0),
                    sauce_s=float(stats.get("sauce_s", 0.0) or 0.0),
                ),
            )
        except OSError:
            pass

    try:
        progress.phase("Backtest (All TA catalog)…", total=len(coins), unit="coins")
        progress.log(f"Pass-1 catalog+deepen on {len(coins)} coins (Sauce deferred)")
        _run_pool(
            coins,
            workers=workers,
            include_sauce=False,
            loader_factory=loader_factory,
            timeframes=tf_list,
            strat_list=strat_list,
            stake=stake,
            fee=fee,
            fee_bps=rp.backtest_fee_bps_round_trip,
            prefs_root=root,
            progress=progress,
            on_ok=lambda s, r, st: _accumulate(s, r, st, tally=True, label="catalog"),
            on_ctx=lambda sym, ctx: market_contexts.__setitem__(sym, ctx),
            on_score=lambda sym, rows: scored.append((sym, oracle_rank_score(rows))),
            include_market_context=mc_with,
        )

        if not sauce_with:
            progress.log("Sauce skipped (sauce_with_scan=false); catalog+deepen complete")
        else:
            sauce_syms = select_sauce_symbols(scored, top_n=sauce_top_n)
            sauce_coins = [coin_by_sym[s] for s in sauce_syms if s in coin_by_sym]
            progress.log(
                f"Sauce: {len(sauce_coins)} of {len(coins)} "
                f"(top{sauce_top_n}; {', '.join(sauce_syms) or 'none'})"
            )
            if sauce_coins and _sauce_pool_on_seeds(
                sauce_coins,
                loader_factory=loader_factory,
                timeframes=tf_list,
                strat_list=strat_list,
                stake=stake,
                fee=fee,
                fee_bps=rp.backtest_fee_bps_round_trip,
                prefs_root=root,
                progress=progress,
                seed_rows_by_symbol=by_symbol,
                on_ok=lambda s, r, st: _accumulate(s, r, st, tally=False, label="sauce"),
                on_ctx=lambda sym, ctx: market_contexts.__setitem__(sym, ctx),
            ):
                mark_sauce_ever(root, sauce_syms)
    finally:
        set_coin_parallel(1)

    results: list[dict[str, Any]] = []
    for coin in coins:
        sym = str(coin.get("symbol") or "").strip().upper()
        if sym and sym in by_symbol:
            results.extend(by_symbol[sym])

    elapsed = time.perf_counter() - started
    phase_s = {
        "ohlcv_load_s": round(load_s, 3),
        "pass1_defaults_s": round(pass1_s, 3),
        "deepen_s": round(deepen_s, 3),
    }
    progress.log(
        f"All-TA done: {len(results)} rows · tested={tested} pruned={pruned} "
        f"deepened={deepened} · sauced={len(sauce_syms)} · {elapsed:.1f}s · "
        f"load={phase_s['ohlcv_load_s']}s pass1={phase_s['pass1_defaults_s']}s "
        f"deepen={phase_s['deepen_s']}s"
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
        "market_contexts": market_contexts,
        "sauce_symbols": sauce_syms,
        "sauce_top_n": sauce_top_n,
        "sauce_with_scan": sauce_with,
    }
