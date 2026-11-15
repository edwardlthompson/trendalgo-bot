"""Thread pool helpers for Opportunity All-TA catalog and Sauce passes."""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from trendalgo.device.opportunity_sauce import mark_sauce_ever
from trendalgo.device.scan_bt_prefs import (
    enabled_strategies,
    load_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_parallel import parallel_log_bits, set_coin_parallel
from trendalgo.device.scan_stake import DEFAULT_SCAN_EXCHANGE, DEVICE_SCAN_STAKE_USD
from trendalgo.device.scanner_all_ta_coin import backtest_one_coin
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange
from trendalgo.scanner.progress import get_scan_progress

CoinResult = tuple[str, list[dict[str, Any]], dict[str, float], dict[str, Any] | None]

__all__ = ["run_opportunity_sauce_pass", "run_pool", "sauce_pool_on_seeds"]


def run_pool(
    coins: list[dict[str, Any]],
    *,
    workers: int,
    include_sauce: bool,
    loader_factory: Any,
    timeframes: tuple[str, ...],
    strat_list: tuple[str, ...],
    stake: float,
    fee: Any,
    fee_bps: float,
    prefs_root: Path,
    progress: Any,
    on_ok: Any,
    on_ctx: Any,
    on_score: Any,
    seed_rows_by_symbol: dict[str, list[dict[str, Any]]] | None = None,
    include_market_context: bool = True,
) -> None:
    n_coins = len(coins)
    if n_coins == 0:
        return
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futs: dict[Future[CoinResult], dict[str, Any]] = {}
        for c in coins:
            sym = str(c.get("symbol") or c.get("pair") or "?")
            sym_key = str(c.get("symbol") or "").strip().upper()
            if include_sauce:
                progress.log(f"Sauce cooking {sym}…")
            seed = None
            if seed_rows_by_symbol is not None and sym_key:
                seed = list(seed_rows_by_symbol.get(sym_key) or [])
            futs[
                pool.submit(
                    backtest_one_coin,
                    c,
                    loader_factory=loader_factory,
                    timeframes=timeframes,
                    strat_list=strat_list,
                    stake=stake,
                    fee=fee,
                    fee_bps_round_trip=fee_bps,
                    prefs_root=prefs_root,
                    include_sauce=include_sauce,
                    sauce_only_rows=seed,
                    include_market_context=include_market_context,
                )
            ] = c
        for fut in as_completed(futs):
            done += 1
            coin = futs[fut]
            fallback = str(coin.get("symbol") or coin.get("pair") or "")
            try:
                symbol, rows, stats, market_context = fut.result()
            except Exception as exc:
                progress.log(f"All-TA coin failed: {exc}", level="error")
                progress.step(done, total=n_coins, pair=fallback)
                continue
            if symbol:
                on_ok(symbol, rows, stats)
                if on_score is not None:
                    on_score(symbol, rows)
                if isinstance(market_context, dict):
                    on_ctx(str(symbol).upper(), market_context)
            progress.step(done, total=n_coins, pair=symbol or fallback)


def sauce_pool_on_seeds(
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
    """Serial Sauce-only pool. Returns True if the pool ran."""
    if not sauce_coins:
        return False
    set_coin_parallel(1)
    progress.phase("Backtest (Secret Sauce)…", total=len(sauce_coins), unit="coins")
    progress.log(
        f"Sauce pass: {len(sauce_coins)} coins · sauce-only · {parallel_log_bits()} (serial)"
    )
    run_pool(
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


def run_opportunity_sauce_pass(
    coins: list[dict[str, Any]],
    *,
    prefs_root: Path,
    seed_rows_by_symbol: dict[str, list[dict[str, Any]]],
    top_n: int | None = None,
) -> dict[str, Any] | None:
    """Sauce-only pass for pre-selected coins (no catalog/deepen)."""
    import os

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
    root = prefs_root
    prefs = load_scan_bt_prefs(root)
    strat_list = enabled_strategies(prefs.strategy_denylist)
    tf_list = selected_timeframes(prefs)
    if not strat_list or not tf_list:
        return None
    n = int(top_n) if top_n is not None else int(prefs.sauce_top_n)
    stake = DEVICE_SCAN_STAKE_USD
    fee = fee_for_exchange(DEFAULT_SCAN_EXCHANGE, rp.backtest_fee_bps_round_trip)
    progress = get_scan_progress()
    by_symbol: dict[str, list[dict[str, Any]]] = {
        k: list(v) for k, v in seed_rows_by_symbol.items()
    }
    market_contexts: dict[str, dict[str, Any]] = {}
    sauce_syms = [
        str(c.get("symbol") or "").strip().upper()
        for c in coins
        if str(c.get("symbol") or "").strip()
    ]

    def loader_factory() -> Any:
        return BacktestDataLoader(
            cache=PriceCache(Path(rp.scanner_db_path)),
            max_cache_age_hours=rp.cache_price_hours,
            loader_params=rp.loader,
        )

    def on_ok(symbol: str, rows: list[dict[str, Any]], _stats: dict[str, float]) -> None:
        by_symbol[symbol] = list(rows)

    started = time.perf_counter()
    try:
        sauce_pool_on_seeds(
            coins,
            loader_factory=loader_factory,
            timeframes=tf_list,
            strat_list=strat_list,
            stake=stake,
            fee=fee,
            fee_bps=rp.backtest_fee_bps_round_trip,
            prefs_root=root,
            progress=progress,
            seed_rows_by_symbol=by_symbol,
            on_ok=on_ok,
            on_ctx=lambda sym, ctx: market_contexts.__setitem__(sym, ctx),
        )
        mark_sauce_ever(root, sauce_syms)
    finally:
        set_coin_parallel(1)

    results: list[dict[str, Any]] = []
    for coin in coins:
        sym = str(coin.get("symbol") or "").strip().upper()
        if sym and sym in by_symbol:
            results.extend(by_symbol[sym])
    return {
        "results": results,
        "coins_processed": len(coins),
        "rows_generated": len(results),
        "elapsed_s": round(time.perf_counter() - started, 3),
        "market_contexts": market_contexts,
        "sauce_symbols": sauce_syms,
        "sauce_top_n": n,
    }
