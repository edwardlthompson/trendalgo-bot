"""TrendAlgo ↔ LTS public snapshot + backtest sweep bridge."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.lts_vendor import install_import_shims
from trendalgo.lts_vendor.chart_closes import attach_chart_closes
from trendalgo.lts_vendor.chart_preserve import preserve_chart_closes
from trendalgo.lts_vendor.public_snapshot import (
    load_public_snapshot,
    write_public_snapshot,
)
from trendalgo.lts_vendor.utils.scan_artifacts import build_public_qualified_snapshot
from trendalgo.scanner.backtest_edge import EDGE_KEYS, bot_vs_bh_edge
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import QualifiedSnapshot

# Keep every valid strategy row per coin (dashboard "Results" shows all of them).
_ALL_STRATEGY_ROWS = 500


def _pair_symbol(pair: str) -> str:
    base = pair.split("/")[0].strip().upper()
    return base or pair.upper()


def _pair_for_symbol(symbol: str) -> str:
    sym = symbol.strip().upper()
    return f"{sym}/USD" if "/" not in sym else sym


def opportunities_to_final_results(snapshot: QualifiedSnapshot) -> list[dict[str, Any]]:
    """Map TrendAlgo v2 opportunities into LTS final_results coin dicts."""
    out: list[dict[str, Any]] = []
    for row in snapshot.opportunities:
        symbol = _pair_symbol(row.pair)
        gain7 = float(row.gain_pct or 0.0) * 100.0
        out.append(
            {
                "symbol": symbol,
                "name": symbol,
                "slug": symbol.lower(),
                "cmc_slug": None,
                "source_url": None,
                "gains": {"7d": gain7, "30d": gain7},
                "uniformity_score": float(row.uniformity or 0.0) * 100.0,
                "current_rank": int(row.rank),
                "rank_delta": 0,
                "listed_on": ["kraken"],
                "volume_24h": float(row.volume_score or 0.0),
                "exchange_volumes": {"kraken": float(row.volume_score or 0.0)},
                "ohlcv_source": "trendalgo_scanner",
                "identity": {
                    "cg_id": symbol.lower(),
                    "cmc_id": None,
                    "cmc_slug": None,
                    "top_coins_provider": "trendalgo",
                    "ohlcv_source": "trendalgo_scanner",
                },
                "gecko_id": symbol.lower(),
                "cg_id": symbol.lower(),
                "pair": row.pair,
            }
        )
    pair_by_symbol = {
        str(c.get("symbol", "")).upper(): str(
            c.get("pair") or _pair_for_symbol(str(c.get("symbol", "")))
        )
        for c in out
    }
    return attach_chart_closes(
        out, lambda symbol: pair_by_symbol.get(symbol, _pair_for_symbol(symbol))
    )


def merge_backtest_into_coins(
    coins: list[dict[str, Any]],
    backtest_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not backtest_summary:
        return coins
    install_import_shims()
    from trendalgo.lts_vendor.backtesting.report import notification_rows_for_symbol

    for coin in coins:
        symbol = str(coin.get("symbol", "")).upper()
        if not symbol:
            continue
        details = notification_rows_for_symbol(backtest_summary, symbol, top_n=_ALL_STRATEGY_ROWS)
        strategies = details.get("top_strategies", [])
        buy_hold = details.get("buy_hold")
        oracle_max = details.get("oracle_max")
        coin["backtest_top_strategies"] = strategies
        coin["backtest_buy_hold"] = buy_hold
        coin["backtest_oracle_max"] = oracle_max
        for key in EDGE_KEYS:
            coin.pop(key, None)
        edge = bot_vs_bh_edge(strategies, buy_hold)
        if edge is not None:
            coin.update(edge)
    return coins


def run_lts_backtest_sweep(final_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not final_results:
        return None
    if os.environ.get("BACKTEST_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return None
    install_import_shims()
    from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings
    from trendalgo.lts_vendor.backtesting.runner import run_backtests_for_final_results

    rp = runner_params_from_settings()
    out_path = Path(rp.base_dir) / "backtest_results.json"
    return run_backtests_for_final_results(
        final_results,
        output_path=out_path,
        params=rp,
        progress=get_scan_progress().backtest_event,
    )


def resolve_scan_interval_seconds() -> int:
    """Prefer ScannerSettings.interval_minutes; fall back to SCAN_INTERVAL_SECONDS or 1h."""
    try:
        from trendalgo.scanner.store import ScannerStore

        data = Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve()
        store = ScannerStore(data / "scanner.db")
        minutes = int(store.get_settings().interval_minutes)
        if minutes >= 1:
            return max(60, minutes * 60)
    except Exception:
        pass
    try:
        return max(60, int(os.environ.get("SCAN_INTERVAL_SECONDS", "3600")))
    except ValueError:
        return 3600


def publish_final_results(
    final_results: list[dict[str, Any]],
    *,
    run_backtests: bool = True,
) -> dict[str, Any]:
    """Write public snapshot from coin rows; keep chart closes across BT republish."""
    progress = get_scan_progress()
    coins = [dict(c) for c in final_results]
    prev_coins = list(load_public_snapshot().get("coins") or [])
    bt_summary: dict[str, Any] | None = None
    if run_backtests and coins:
        try:
            bt_summary = run_lts_backtest_sweep(coins)
        except Exception as exc:
            progress.log(f"Backtest sweep failed: {exc}", level="error")
            bt_summary = None
    merge_backtest_into_coins(coins, bt_summary)
    preserve_chart_closes(coins, prev_coins)
    interval = resolve_scan_interval_seconds()
    with_bt = sum(
        1 for c in coins if c.get("backtest_buy_hold") or c.get("backtest_top_strategies")
    )
    with_vol = sum(1 for c in coins if c.get("volume_acceleration_pct") is not None)
    progress.set_counts(coins=len(coins), backtest_coins=with_bt, vol_delta_coins=with_vol)
    progress.log(
        f"Publishing LTS snapshot: {len(coins)} coins · {with_bt} with backtests "
        f"· {with_vol} with Vol Δ%",
        level="success" if with_bt == len(coins) and with_vol == len(coins) else "info",
    )
    payload = build_public_qualified_snapshot(
        coins,
        field_set="full",
        scan_interval_seconds=interval,
        scan_health={
            "scan_duration_s": 0,
            "coins_evaluated": len(coins),
            "errors_count": 0,
        },
    )
    payload["updated_at"] = datetime.now(UTC).isoformat()
    write_public_snapshot(payload)
    return payload


def publish_from_v2_snapshot(
    snapshot: QualifiedSnapshot,
    *,
    run_backtests: bool = True,
    final_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    coins = final_results if final_results is not None else opportunities_to_final_results(snapshot)
    return publish_final_results(coins, run_backtests=run_backtests)


def refresh_public_snapshot_from_store(snapshot: QualifiedSnapshot | None) -> dict[str, Any]:
    if snapshot is None or not snapshot.opportunities:
        return load_public_snapshot()
    return publish_from_v2_snapshot(snapshot, run_backtests=True)
