"""Backtest worker pool (D1, D2). Spawn-based. Terminated on cancel and when the process exits.

Nothing here imports Qt, so a frozen worker can start without a window.
"""

from __future__ import annotations

import atexit
import multiprocessing
from collections.abc import Callable
from multiprocessing.pool import AsyncResult, Pool
from typing import Any

DEFAULT_WORKERS = 2


class WorkerPool:
    def __init__(self, workers: int = DEFAULT_WORKERS) -> None:
        if workers < 1:
            raise ValueError("a pool needs at least one worker")
        self.workers = workers
        self._pool: Pool | None = None
        atexit.register(self.shutdown)

    def submit(self, fn: Callable[..., Any], *args: Any) -> AsyncResult[Any]:
        if self._pool is None:
            self._pool = multiprocessing.get_context("spawn").Pool(self.workers)
        return self._pool.apply_async(fn, args)

    def cancel(self) -> None:
        """Kill every worker now. Jobs in flight stop; the next submit starts a fresh pool."""
        pool, self._pool = self._pool, None
        if pool is not None:
            pool.terminate()
            pool.join()

    def shutdown(self) -> None:
        self.cancel()
