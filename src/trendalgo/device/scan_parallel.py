"""Shared CPU budget for nested All-TA coin × catalog workers."""

from __future__ import annotations

import os

_coin_parallel: int = 1


def cpu_budget() -> int:
    """Usable cores for scan work (leave one for the UI)."""
    return max(1, int(os.cpu_count() or 4) - 1)


def set_coin_parallel(n: int) -> None:
    """How many coins run concurrently (Opportunity); Backtest leaves 1."""
    global _coin_parallel
    _coin_parallel = max(1, int(n))


def coin_parallel() -> int:
    return max(1, int(_coin_parallel))


def all_ta_coin_workers() -> int:
    """Outer coin pool size. Env TRENDALGO_ALL_TA_WORKERS wins when set."""
    raw = os.environ.get("TRENDALGO_ALL_TA_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(24, int(raw)))
        except ValueError:
            pass
    budget = cpu_budget()
    # Cap outer coins at 8 so pass2 keeps ~budget/3 workers without spiking memory on large sweeps.
    return max(1, min(budget // 3, 8))


def all_ta_sauce_workers(n_coins: int = 1) -> int:
    """Worker count for multi-coin Secret Sauce pass. Env TRENDALGO_SAUCE_WORKERS wins."""
    raw = os.environ.get("TRENDALGO_SAUCE_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(int(n_coins), 24, int(raw)))
        except ValueError:
            pass
    return max(1, min(int(n_coins), cpu_budget(), 16))


def pass2_worker_count() -> int:
    """Per-coin catalog / deepen workers. Env TRENDALGO_PASS2_WORKERS wins."""
    raw = os.environ.get("TRENDALGO_PASS2_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(24, int(raw)))
        except ValueError:
            pass
    return max(1, cpu_budget() // coin_parallel())


def parallel_log_bits() -> str:
    return f"parallel coins={coin_parallel()} pass2={pass2_worker_count()} budget={cpu_budget()}"
