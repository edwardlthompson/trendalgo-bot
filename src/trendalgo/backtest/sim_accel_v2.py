"""Numba nogil SIM-01/SIM-02 kernel (fill_offset + open/high/low + slippage)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

_sim_v2_fn: Any = None


def ensure_sim_v2_kernel() -> Any:
    global _sim_v2_fn
    if _sim_v2_fn is not None:
        return _sim_v2_fn
    from numba import njit  # noqa: PLC0415

    njit_dec: Callable[[Any], Any] = njit(cache=True, nogil=True)

    @njit_dec
    def _sim_v2(
        c: np.ndarray,
        o: np.ndarray,
        h: np.ndarray,
        lo: np.ndarray,
        en: np.ndarray,
        ex: np.ndarray,
        stake: float,
        fee: float,
        stop: float,
        offset: int,
        slip_bps: float,
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
        pending_entry = 0
        pending_exit = 0
        n = c.shape[0]
        entry_mult = 1.0 + (slip_bps / 10000.0 if slip_bps > 0.0 else 0.0)
        exit_mult = 1.0 - (slip_bps / 10000.0 if slip_bps > 0.0 else 0.0)
        if exit_mult < 0.0:
            exit_mult = 0.0

        for i in range(1, n):
            if pending_entry > 0 and not in_pos:
                pending_entry -= 1
                if pending_entry == 0:
                    in_pos = True
                    entry_price = float(c[i]) * entry_mult
                    peak_price = float(h[i])
            if in_pos and pending_exit > 0:
                pending_exit -= 1
                if pending_exit == 0:
                    px = float(c[i]) * exit_mult
                    g = stake * ((px / entry_price) - 1.0) if entry_price != 0.0 else 0.0
                    gross += g
                    fees_paid += fee
                    trades += 1
                    if g - fee > 0.0:
                        wins += 1
                    in_pos = False
                    entry_price = 0.0
                    peak_price = 0.0
                    continue
            if (not in_pos) and pending_entry == 0 and en[i]:
                if offset == 0:
                    in_pos = True
                    entry_price = float(c[i]) * entry_mult
                    peak_price = float(h[i])
                else:
                    pending_entry = offset
                continue
            if (not in_pos) or pending_exit > 0:
                continue
            hi = float(h[i])
            if hi > peak_price:
                peak_price = hi
            stop_px = peak_price * (1.0 - stop) if stop > 0.0 else 0.0
            if stop > 0.0 and float(lo[i]) <= stop_px:
                op = float(o[i])
                fill = op if op < stop_px else stop_px
                px = fill * exit_mult
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
                continue
            if ex[i]:
                if offset == 0:
                    px = float(c[i]) * exit_mult
                    g = stake * ((px / entry_price) - 1.0) if entry_price != 0.0 else 0.0
                    gross += g
                    fees_paid += fee
                    trades += 1
                    if g - fee > 0.0:
                        wins += 1
                    in_pos = False
                    entry_price = 0.0
                    peak_price = 0.0
                else:
                    pending_exit = offset
        if in_pos and entry_price != 0.0:
            px = float(c[n - 1]) * exit_mult
            g = stake * ((px / entry_price) - 1.0)
            gross += g
            fees_paid += fee
            trades += 1
            open_trades = 1
        return gross, fees_paid, trades, wins, tsl_hits, open_trades

    _sim_v2_fn = _sim_v2
    return _sim_v2_fn


def numba_sim_v2(
    closes: np.ndarray,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    stake_usd: float,
    fee_per_trade: float,
    tsl: float,
    fill_offset: int,
    slippage_bps: float,
) -> tuple[float, float, int, int, int, int]:
    fn = ensure_sim_v2_kernel()
    res = fn(
        closes,
        opens,
        highs,
        lows,
        entries,
        exits,
        float(stake_usd),
        float(fee_per_trade),
        max(0.0, float(tsl)),
        max(0, int(fill_offset)),
        max(0.0, float(slippage_bps)),
    )
    return (float(res[0]), float(res[1]), int(res[2]), int(res[3]), int(res[4]), int(res[5]))
