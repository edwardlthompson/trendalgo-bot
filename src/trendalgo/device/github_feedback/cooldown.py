"""60s cooldown shared by Open GitHub duplicate search."""

from __future__ import annotations

from collections.abc import Callable
from time import time

COOLDOWN_MS = 60_000
Clock = Callable[[], float]


class Cooldown[T]:
    def __init__(self, now: Clock | None = None) -> None:
        self._now: Clock = now or (lambda: time() * 1000)
        self._last_at = 0.0
        self._last_search: T | None = None

    def can_act(self) -> bool:
        return self._now() - self._last_at >= COOLDOWN_MS

    def mark(self) -> None:
        self._last_at = self._now()

    def cached_search(self, fresh: T) -> T:
        if self._now() - self._last_at < COOLDOWN_MS and self._last_search is not None:
            return self._last_search
        self._last_search = fresh
        self._last_at = self._now()
        return fresh

    def peek_search(self) -> T | None:
        if self._now() - self._last_at < COOLDOWN_MS and self._last_search is not None:
            return self._last_search
        return None


def create_cooldown(now: Clock | None = None) -> Cooldown[object]:
    return Cooldown(now)
