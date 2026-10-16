"""Rate-limit gate stub for vendored LTS clients."""

from __future__ import annotations

import time


class MinIntervalGate:
    def __init__(self, calls_per_minute: int = 30) -> None:
        self._min_interval = 60.0 / max(1, int(calls_per_minute))
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delay = self._min_interval - (now - self._last)
        if delay > 0:
            time.sleep(min(delay, 1.0))
        self._last = time.monotonic()
