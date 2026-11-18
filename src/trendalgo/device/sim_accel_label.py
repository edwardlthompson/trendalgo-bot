"""Honest accel labels: catalog is SIM-01 python; TSL grids may use numba/cuda."""

from __future__ import annotations

from trendalgo.backtest.sim_accel import accel_backend


def catalog_accel_label() -> str:
    """Catalog / backtest_one uses SIM-01 (fill_offset+OHLC) → python path today."""
    grid = accel_backend()
    return f"accel=python(SIM-01); tsl_grid={grid}"


def warm_tsl_grid_kernels() -> None:
    """JIT-warm closes-only TSL grid kernels once (no-op if python backend)."""
    if accel_backend() == "python":
        return
    try:
        import numpy as np

        from trendalgo.backtest.sim_accel import simulate_tsl_grid
        from trendalgo.exchanges.fees import ExchangeFeeSchedule

        closes = np.linspace(100.0, 110.0, 64, dtype=float)
        entries = np.zeros(64, dtype=bool)
        exits = np.zeros(64, dtype=bool)
        entries[10] = True
        exits[40] = True
        fee = ExchangeFeeSchedule(
            exchange_id="warm", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
        )
        list(simulate_tsl_grid(closes, entries, exits, (0.01, 0.02), stake_usd=1000.0, fee=fee))
    except Exception:
        return
