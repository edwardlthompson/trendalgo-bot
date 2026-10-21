"""Per-coin All-TA backtest — same keep/deepen rules as the Backtest tab."""

from __future__ import annotations

import time
from typing import Any

from trendalgo.device.pair_strategy_scan import scan_pair_strategies


def backtest_one_coin(
    coin: dict[str, Any],
    *,
    loader_factory: Any,
    timeframes: tuple[str, ...],
    strat_list: tuple[str, ...],
    stake: float,
    fee: Any,
    fee_bps_round_trip: float | None = None,
) -> tuple[str, list[dict[str, Any]], dict[str, float]]:
    """Run the Backtest-tab All-TA path for one Opportunity coin."""
    from trendalgo.device.scan_identity import coin_exchange_id
    from trendalgo.device.scanner_all_ta_prune import fee_for_exchange

    symbol = str(coin.get("symbol") or "").strip().upper()
    stats = {
        "tested": float(len(strat_list) * len(timeframes)),
        "pruned": 0.0,
        "deepened": 0.0,
        "load_s": 0.0,
        "pass1_s": 0.0,
        "deepen_s": 0.0,
    }
    if not symbol:
        return symbol, [], {**stats, "elapsed_s": 0.0}
    t0 = time.perf_counter()
    pair = str(coin.get("pair") or "") or f"{symbol}/USD"
    gecko = coin.get("gecko_id")
    gecko_id = str(gecko) if gecko else None
    loader = loader_factory()
    use_fee = fee
    if fee_bps_round_trip is not None:
        use_fee = fee_for_exchange(coin_exchange_id(coin), fee_bps_round_trip)
    rows = scan_pair_strategies(
        symbol=symbol,
        pair=pair,
        timeframes=timeframes,
        strat_list=strat_list,
        stake=stake,
        fee=use_fee,
        loader=loader,
        gecko_id=gecko_id,
    )
    deepened = sum(1 for r in rows if r.get("optimized"))
    stats["deepened"] = float(deepened)
    stats["elapsed_s"] = time.perf_counter() - t0
    return symbol, rows, stats
