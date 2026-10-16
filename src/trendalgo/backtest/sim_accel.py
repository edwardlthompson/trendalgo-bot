"""Accelerated fee-aware bar sims: cuda → numba → python."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np

from trendalgo.exchanges.fees import ExchangeFeeSchedule

_CUDA_GRID_MIN = 8


@lru_cache(maxsize=1)
def accel_backend() -> str:
    """Return cuda, numba, or python (first available)."""
    try:
        from numba import cuda as nbcuda  # noqa: PLC0415

        if bool(nbcuda.is_available()):  # type: ignore[no-untyped-call,unused-ignore]
            return "cuda"
    except Exception:
        pass
    try:
        import numba  # noqa: F401, PLC0415

        return "numba"
    except Exception:
        return "python"


def simulate_arrays(
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    stake_usd: float,
    fee_per_trade: float,
    trailing_stop_pct: float,
) -> tuple[float, float, int, int, int, int]:
    """Return gross, fees, trades, wins, tsl_hits, open_trades."""
    if accel_backend() in {"numba", "cuda"}:
        try:
            from trendalgo.backtest.sim_accel_kernels import numba_one  # noqa: PLC0415

            return numba_one(closes, entries, exits, stake_usd, fee_per_trade, trailing_stop_pct)
        except Exception:
            pass
    return python_one(closes, entries, exits, stake_usd, fee_per_trade, trailing_stop_pct)


def simulate_tsl_grid(
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    tsls: tuple[float, ...] | list[float],
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> list[dict[str, Any]]:
    """Simulate each TSL; CUDA batch when available and grid is large enough."""
    fee_per = float(fee.round_trip_taker_cost(stake_usd))
    closes_f = np.ascontiguousarray(closes, dtype=np.float64)
    entries_b = np.ascontiguousarray(entries.astype(np.bool_), dtype=np.bool_)
    exits_b = np.ascontiguousarray(exits.astype(np.bool_), dtype=np.bool_)
    tsl_arr = np.asarray([max(0.0, float(t)) for t in tsls], dtype=np.float64)
    if accel_backend() == "cuda" and len(tsl_arr) >= _CUDA_GRID_MIN:
        try:
            from trendalgo.backtest.sim_accel_kernels import cuda_tsl_grid  # noqa: PLC0415

            rows = cuda_tsl_grid(closes_f, entries_b, exits_b, tsl_arr, stake_usd, fee_per)
            return [pack_stats(r, fee) for r in rows]
        except Exception:
            pass
    out: list[dict[str, Any]] = []
    for tsl in tsl_arr:
        gross, fees, trades, wins, hits, open_n = simulate_arrays(
            closes_f,
            entries_b,
            exits_b,
            stake_usd=stake_usd,
            fee_per_trade=fee_per,
            trailing_stop_pct=float(tsl),
        )
        out.append(pack_stats((gross, fees, trades, wins, hits, open_n, float(tsl)), fee))
    return out


def pack_stats(row: tuple[float, ...], fee: ExchangeFeeSchedule) -> dict[str, Any]:
    # (gross, fees, trades, wins, hits, open, tsl) — accept legacy 6-tuples without open.
    # Index via list so pyright does not reject variable-length tuple subscripting.
    vals = list(row)
    if len(vals) >= 7:
        gross, fees, trades, wins, hits, open_n, tsl = (
            vals[0],
            vals[1],
            int(vals[2]),
            int(vals[3]),
            int(vals[4]),
            int(vals[5]),
            float(vals[6]),
        )
    else:
        gross, fees, trades, wins, hits, tsl = (
            vals[0],
            vals[1],
            int(vals[2]),
            int(vals[3]),
            int(vals[4]),
            float(vals[5]),
        )
        open_n = 0
    net = gross - fees
    closed = max(0, trades - open_n)
    win_rate = (wins / closed) if closed else 0.0
    return {
        "gross_profit": round(gross, 4),
        "fees_paid": round(fees, 4),
        "net_profit": round(net, 4),
        "trades": trades,
        "wins": wins,
        "open_trades": open_n,
        "tsl_hits": hits,
        "win_rate": round(win_rate, 4),
        "fee_taker_pct": fee.taker_pct,
        "trailing_stop_pct": tsl,
    }


def python_one(
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    stake_usd: float,
    fee_per_trade: float,
    tsl: float,
) -> tuple[float, float, int, int, int, int]:
    gross = 0.0
    fees_paid = 0.0
    trades = 0
    wins = 0
    tsl_hits = 0
    open_trades = 0
    in_pos = False
    entry_price = 0.0
    peak_price = 0.0
    n = len(closes)
    for i in range(1, n):
        if not in_pos and entries[i]:
            in_pos = True
            entry_price = float(closes[i])
            peak_price = entry_price
        elif in_pos:
            px = float(closes[i])
            peak_price = max(peak_price, px)
            stop_hit = tsl > 0 and px <= peak_price * (1.0 - tsl)
            if exits[i] or stop_hit:
                if stop_hit:
                    tsl_hits += 1
                gross_pnl = stake_usd * ((px / entry_price) - 1.0) if entry_price else 0.0
                gross += gross_pnl
                fees_paid += fee_per_trade
                trades += 1
                if gross_pnl - fee_per_trade > 0:
                    wins += 1
                in_pos = False
                entry_price = 0.0
                peak_price = 0.0
    if in_pos and entry_price:
        px = float(closes[n - 1])
        gross_pnl = stake_usd * ((px / entry_price) - 1.0)
        gross += gross_pnl
        fees_paid += fee_per_trade
        trades += 1
        open_trades = 1
    return gross, fees_paid, trades, wins, tsl_hits, open_trades
