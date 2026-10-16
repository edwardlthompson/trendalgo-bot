"""Numba/CUDA kernels for fee-aware bar sims (optional deps)."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

_numba_run: Any = None


def numba_one(
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    stake_usd: float,
    fee_per_trade: float,
    tsl: float,
) -> tuple[float, float, int, int, int, int]:
    global _numba_run
    if _numba_run is None:
        from numba import njit  # noqa: PLC0415

        @njit(cache=True)
        def _run(
            c: np.ndarray, en: np.ndarray, ex: np.ndarray, stake: float, fee: float, stop: float
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
            n = c.shape[0]
            for i in range(1, n):
                if (not in_pos) and en[i]:
                    in_pos = True
                    entry_price = float(c[i])
                    peak_price = entry_price
                elif in_pos:
                    px = float(c[i])
                    if px > peak_price:
                        peak_price = px
                    stop_hit = stop > 0.0 and px <= peak_price * (1.0 - stop)
                    if ex[i] or stop_hit:
                        if stop_hit:
                            tsl_hits += 1
                        g = stake * ((px / entry_price) - 1.0) if entry_price != 0.0 else 0.0
                        gross += g
                        fees_paid += fee
                        trades += 1
                        if g - fee > 0.0:
                            wins += 1
                        in_pos = False
                        entry_price = 0.0
                        peak_price = 0.0
            if in_pos and entry_price != 0.0:
                px = float(c[n - 1])
                g = stake * ((px / entry_price) - 1.0)
                gross += g
                fees_paid += fee
                trades += 1
                open_trades = 1
            return gross, fees_paid, trades, wins, tsl_hits, open_trades

        _numba_run = _run
    result = cast(
        tuple[Any, ...], _numba_run(closes, entries, exits, stake_usd, fee_per_trade, tsl)
    )
    return (
        float(result[0]),
        float(result[1]),
        int(result[2]),
        int(result[3]),
        int(result[4]),
        int(result[5]),
    )


def cuda_tsl_grid(
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    tsls: np.ndarray,
    stake_usd: float,
    fee_per_trade: float,
) -> list[tuple[float, float, int, int, int, int, float]]:
    from numba import cuda  # noqa: PLC0415

    n_tsl = int(tsls.shape[0])
    out = np.zeros((n_tsl, 6), dtype=np.float64)
    d_c, d_en, d_ex = cuda.to_device(closes), cuda.to_device(entries), cuda.to_device(exits)
    d_tsl, d_out = cuda.to_device(tsls), cuda.to_device(out)

    @cuda.jit
    def kernel(c, en, ex, stops, stake, fee, dest):  # noqa: ANN001
        tid = cuda.grid(1)
        if tid >= stops.shape[0]:
            return
        stop = stops[tid]
        gross = fees_paid = 0.0
        trades = wins = tsl_hits = open_trades = 0
        in_pos = False
        entry_price = peak_price = 0.0
        n = c.shape[0]
        for i in range(1, n):
            if (not in_pos) and en[i]:
                in_pos = True
                entry_price = peak_price = c[i]
            elif in_pos:
                px = c[i]
                if px > peak_price:
                    peak_price = px
                stop_hit = stop > 0.0 and px <= peak_price * (1.0 - stop)
                if ex[i] or stop_hit:
                    if stop_hit:
                        tsl_hits += 1
                    g = stake * ((px / entry_price) - 1.0) if entry_price != 0.0 else 0.0
                    gross += g
                    fees_paid += fee
                    trades += 1
                    if g - fee > 0.0:
                        wins += 1
                    in_pos = False
                    entry_price = peak_price = 0.0
        if in_pos and entry_price != 0.0:
            g = stake * ((c[n - 1] / entry_price) - 1.0)
            gross += g
            fees_paid += fee
            trades += 1
            open_trades = 1
        dest[tid, 0] = gross
        dest[tid, 1] = fees_paid
        dest[tid, 2] = trades
        dest[tid, 3] = wins
        dest[tid, 4] = tsl_hits
        dest[tid, 5] = open_trades

    kernel[1, max(32, n_tsl)](d_c, d_en, d_ex, d_tsl, stake_usd, fee_per_trade, d_out)
    cuda.synchronize()
    host = d_out.copy_to_host()
    return [
        (
            float(host[i, 0]),
            float(host[i, 1]),
            int(host[i, 2]),
            int(host[i, 3]),
            int(host[i, 4]),
            int(host[i, 5]),
            float(tsls[i]),
        )
        for i in range(n_tsl)
    ]
