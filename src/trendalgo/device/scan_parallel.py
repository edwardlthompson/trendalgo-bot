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
    # Cap outer coins at 10 so pass2 keeps ~budget/3 workers on high-core CPUs.
    return max(1, min(budget // 3, 10))


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
