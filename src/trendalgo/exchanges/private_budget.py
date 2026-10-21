"""Per-venue private API RateBudget shared by sync, bots, and key verify (Phase 1b)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from trendalgo.market.rate_budget import RateBudget, call_with_backoff

_BUDGETS: dict[str, RateBudget] = {}
_LOCK = threading.Lock()
_DEFAULT_MAX_PER_MIN = 15


def budget_for(exchange_id: str, *, max_per_min: int | None = None) -> RateBudget:
    limit = max(1, int(max_per_min or _DEFAULT_MAX_PER_MIN))
    with _LOCK:
        existing = _BUDGETS.get(exchange_id)
        if existing is None or existing.max_calls != limit:
            _BUDGETS[exchange_id] = RateBudget(limit, window_s=60.0)
        return _BUDGETS[exchange_id]


def reset_budgets() -> None:
    with _LOCK:
        _BUDGETS.clear()


def acquire_private_slot(exchange_id: str, *, max_per_min: int | None = None) -> bool:
    return budget_for(exchange_id, max_per_min=max_per_min).try_acquire(time.monotonic())


def budget_snapshot(
    exchange_id: str, *, max_per_min: int | None = None, now: float | None = None
) -> dict[str, float | int]:
    """Read-only used/remaining for Settings meters."""
    return budget_for(exchange_id, max_per_min=max_per_min).snapshot(
        time.monotonic() if now is None else now
    )


def call_private[T](
    exchange_id: str,
    call: Callable[[], T],
    *,
    max_per_min: int | None = None,
    retry_on: tuple[type[BaseException], ...] = (),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Acquire a budget slot then run call (with optional rate-limit backoff)."""
    if not acquire_private_slot(exchange_id, max_per_min=max_per_min):
        raise RuntimeError(f"private_rate_budget_exhausted:{exchange_id}")
    if retry_on:
        return call_with_backoff(call, retry_on=retry_on, sleep=sleep)
    return call()
