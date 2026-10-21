"""Worker entry for Backtest-tab pair All-TA scan."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from trendalgo.backtest.heartbeat_tf import needs_1m_base
from trendalgo.backtest.sim_accel import accel_backend
from trendalgo.device.pair_scan_partial import clear_partial_rows, write_partial_rows
from trendalgo.device.pair_scan_progress import clear_progress, write_progress
from trendalgo.device.pair_strategy_scan import scan_pair_strategies
from trendalgo.device.scan_bt_prefs import (
    enabled_strategies,
    load_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_stake import DEFAULT_SCAN_EXCHANGE, DEVICE_SCAN_STAKE_USD
from trendalgo.device.scan_time_history import TimingSample, record_sample
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange


def pair_strategy_scan_job(root: Path, pair: str) -> list[dict[str, Any]]:
    """Worker entry: All-TA settings + progress file under the profile."""
    clear_progress(root)
    clear_partial_rows(root)
    text = str(pair or "").strip().upper()
    if not text or "/" not in text:
        write_progress(root, {"message": "Pair must look like BTC/USD", "phase": "error"})
        raise ValueError("pair must be BASE/QUOTE")

    prefs = load_scan_bt_prefs(root)
    strat_list = enabled_strategies(prefs.strategy_denylist)
    timeframes = selected_timeframes(prefs)
    if not strat_list:
        write_progress(root, {"message": "No strategies enabled", "phase": "error"})
        raise ValueError("no strategies enabled")
    if not timeframes:
        write_progress(root, {"message": "No timeframes enabled", "phase": "error"})
        raise ValueError("no timeframes enabled")

    from trendalgo.lts_vendor import install_import_shims

    install_import_shims()
    from trendalgo.lts_vendor.backtesting.data_loader import BacktestDataLoader
    from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings
    from trendalgo.lts_vendor.shims.database_cache import PriceCache

    rp = runner_params_from_settings()
    stake = DEVICE_SCAN_STAKE_USD
    fee = fee_for_exchange(DEFAULT_SCAN_EXCHANGE, rp.backtest_fee_bps_round_trip)
    symbol = text.split("/", 1)[0].strip().upper()
    loader = BacktestDataLoader(
        cache=PriceCache(Path(rp.scanner_db_path)),
        max_cache_age_hours=rp.cache_price_hours,
        loader_params=rp.loader,
    )
    total = max(1, len(timeframes) * max(1, len(strat_list)))
    subhour = needs_1m_base(timeframes)
    write_progress(
        root,
        {
            "message": (
                f"Starting All-TA scan for {text} ({len(timeframes)} TFs) · "
                f"stake=${stake:.0f} · fees={fee.exchange_id} "
                f"taker={fee.taker_pct * 100:.2f}% · accel={accel_backend()}"
                + (" · 1m base" if subhour else "")
            ),
            "phase": "start",
            "done": 0,
            "total": total,
        },
    )
    t0 = time.perf_counter()
    rows = scan_pair_strategies(
        symbol=symbol,
        pair=text,
        timeframes=timeframes,
        strat_list=strat_list,
        stake=stake,
        fee=fee,
        loader=loader,
        on_progress=lambda payload: write_progress(root, payload),
        on_rows=lambda r: write_partial_rows(root, r),
    )
    try:
        record_sample(
            root,
            TimingSample(
                elapsed_s=time.perf_counter() - t0,
                n_strategies=len(strat_list),
                n_timeframes=len(timeframes),
                had_subhour=subhour,
                ts=time.time(),
            ),
        )
    except OSError:
        pass
    return rows
