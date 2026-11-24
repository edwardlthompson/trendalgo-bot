"""Batched Numba nogil TSL-grid and RSX-neighborhood kernels."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from trendalgo.backtest.sim_accel_v2 import ensure_sim_v2_kernel

_grid_v2_fn: Any = None
_rsx_best_fn: Any = None


def _ensure_batch_kernels() -> tuple[Any, Any]:
    global _grid_v2_fn, _rsx_best_fn
    if _grid_v2_fn is not None and _rsx_best_fn is not None:
        return _grid_v2_fn, _rsx_best_fn
    from numba import njit  # noqa: PLC0415

    sim_v2 = ensure_sim_v2_kernel()
    njit_dec: Callable[[Any], Any] = njit(cache=True, nogil=True)

    @njit_dec
    def _grid_v2(
        c: np.ndarray,
        o: np.ndarray,
        h: np.ndarray,
        lo: np.ndarray,
        en: np.ndarray,
        ex: np.ndarray,
        stops: np.ndarray,
        stake: float,
        fee: float,
        offset: int,
        slip_bps: float,
    ) -> np.ndarray:
        m = stops.shape[0]
        out = np.zeros((m, 6), dtype=np.float64)
        for idx in range(m):
            g, f, tr, w, th, op = sim_v2(
                c, o, h, lo, en, ex, stake, fee, float(stops[idx]), offset, slip_bps
            )
            out[idx, 0] = g
            out[idx, 1] = f
            out[idx, 2] = float(tr)
            out[idx, 3] = float(w)
            out[idx, 4] = float(th)
            out[idx, 5] = float(op)
        return out

    @njit_dec
    def _rsx_best(
        c: np.ndarray,
        o: np.ndarray,
        h: np.ndarray,
        lo: np.ndarray,
        em_mat: np.ndarray,
        ep_arr: np.ndarray,
        el_arr: np.ndarray,
        tag_arr: np.ndarray,
        xm_mat: np.ndarray,
        xp_arr: np.ndarray,
        xl_arr: np.ndarray,
        stake: float,
        fee: float,
        peer_period: int,
        peer_el: int,
        peer_xl: int,
        max_trades: int,
    ) -> tuple[bool, int, int, float]:
        has_best = False
        best_ei = 0
        best_xi = 0
        best_net = 0.0
        n_e = em_mat.shape[0]
        n_x = xm_mat.shape[0]
        for ei in range(n_e):
            ep = int(ep_arr[ei])
            el = int(el_arr[ei])
            tag = int(tag_arr[ei])
            em = em_mat[ei]
            for xi in range(n_x):
                xl = int(xl_arr[xi])
                if el >= xl:
                    continue
                xp = int(xp_arr[xi])
                if (
                    ep == peer_period
                    and xp == peer_period
                    and el == peer_el
                    and xl == peer_xl
                    and tag == 0
                ):
                    continue
                g, f, tr, _w, _th, _op = sim_v2(
                    c, o, h, lo, em, xm_mat[xi], stake, fee, 0.0, 1, 0.0
                )
                if tr < 1 or tr > max_trades:
                    continue
                net = round(g - f, 4)
                if (not has_best) or net > best_net:
                    has_best = True
                    best_net = net
                    best_ei = ei
                    best_xi = xi
        return has_best, best_ei, best_xi, best_net

    _grid_v2_fn = _grid_v2
    _rsx_best_fn = _rsx_best
    return _grid_v2_fn, _rsx_best_fn


def numba_tsl_grid_v2(
    closes: np.ndarray,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    tsls: np.ndarray,
    stake_usd: float,
    fee_per_trade: float,
    fill_offset: int,
    slippage_bps: float,
) -> np.ndarray:
    gfn, _ = _ensure_batch_kernels()
    res: np.ndarray = gfn(
        closes,
        opens,
        highs,
        lows,
        entries,
        exits,
        tsls,
        float(stake_usd),
        float(fee_per_trade),
        max(0, int(fill_offset)),
        max(0.0, float(slippage_bps)),
    )
    return res


def numba_rsx_best(
    closes: np.ndarray,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    em_mat: np.ndarray,
    ep_arr: np.ndarray,
    el_arr: np.ndarray,
    tag_arr: np.ndarray,
    xm_mat: np.ndarray,
    xp_arr: np.ndarray,
    xl_arr: np.ndarray,
    stake_usd: float,
    fee_per_trade: float,
    peer_period: int,
    peer_el: int,
    peer_xl: int,
    max_trades: int,
) -> tuple[bool, int, int, float]:
    _, rfn = _ensure_batch_kernels()
    ok, ei, xi, net = rfn(
        closes,
        opens,
        highs,
        lows,
        em_mat,
        ep_arr,
        el_arr,
        tag_arr,
        xm_mat,
        xp_arr,
        xl_arr,
        float(stake_usd),
        float(fee_per_trade),
        int(peer_period),
        int(peer_el),
        int(peer_xl),
        int(max_trades),
    )
    return bool(ok), int(ei), int(xi), float(net)
