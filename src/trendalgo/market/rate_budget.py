"""Call budget and exponential backoff for the public REST path (E7).

RateBudget is a sliding window: at most max_calls in any window_s seconds. The caller passes the
clock reading, so tests drive time directly. call_with_backoff retries only the errors the caller
names (rate limits), waiting base, 2x base, 4x base, and so on, up to a cap.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable


class RateBudget:
    """At most max_calls in any window of window_s seconds."""

    def __init__(self, max_calls: int, window_s: float = 60.0) -> None:
        if max_calls < 1 or window_s <= 0:
            raise ValueError("a budget needs max_calls >= 1 and window_s > 0")
        self.max_calls = max_calls
        self.window_s = window_s
        self._stamps: deque[float] = deque()

    def try_acquire(self, now: float) -> bool:
        """Take one call slot at time now. Returns False, taking nothing, when the window is full."""
        self._prune(now)
        if len(self._stamps) >= self.max_calls:
            return False
        self._stamps.append(now)
        return True

    def used(self, now: float) -> int:
        """Calls counted in the current window (read-only)."""
        self._prune(now)
        return len(self._stamps)

    def remaining(self, now: float) -> int:
        return max(0, self.max_calls - self.used(now))

    def snapshot(self, now: float) -> dict[str, float | int]:
        return {
            "used": self.used(now),
            "remaining": self.remaining(now),
            "max_calls": self.max_calls,
            "window_s": self.window_s,
        }

    def _prune(self, now: float) -> None:
        while self._stamps and now - self._stamps[0] >= self.window_s:
            self._stamps.popleft()


def backoff_seconds(attempt: int, *, base: float = 1.0, cap: float = 60.0) -> float:
    """Seconds to wait before retry number attempt (0 for the first retry): doubles, then caps."""
    return min(cap, base * 2.0**attempt)


def call_with_backoff[T](
    call: Callable[[], T],
    *,
    retry_on: tuple[type[BaseException], ...],
    sleep: Callable[[float], None],
    attempts: int = 4,
) -> T:
    """Run call. On a retryable error, wait backoff_seconds and try again, up to attempts tries."""
    attempt = 0
    while True:
        try:
            return call()
        except retry_on:
            if attempt + 1 >= attempts:
                raise
            sleep(backoff_seconds(attempt))
            attempt += 1
