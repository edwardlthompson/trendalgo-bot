"""Exact count of finished backtests for the sweep progress feed.

One backtest is one strategy (an indicator, or B&H) on one timeframe of one coin, so a
sweep runs ``coins * timeframes * (indicators + 1)`` of them. Pool workers cannot reach
the parent's progress object, so each worker sends ``("step", symbol)`` for every finished
backtest and ``("done", symbol)`` when its coin ends, however it ends. The parent applies
those messages. A coin counts at most ``per_coin`` steps, and a coin that closes early
(failure, timeout, lost message) is topped up, so the total always reaches the planned
count and never passes it.
"""

from __future__ import annotations

import queue
from collections.abc import Callable, Sequence
from typing import Any, Protocol

STEP = "step"
DONE = "done"
EVENT = "bt_count"


class MessageSource(Protocol):
    def get_nowait(self) -> object: ...


class CallbackSink:
    """In-process stand-in for a worker queue: applies each message at once."""

    def __init__(self, on_message: Callable[[object], None]) -> None:
        self._on_message = on_message

    def put_nowait(self, message: object) -> None:
        self._on_message(message)


class BacktestCounter:
    """Monotonic count of finished backtests across one sweep."""

    def __init__(
        self,
        symbols: Sequence[str],
        *,
        timeframes: int,
        strategies: int,
        emit: Callable[[dict[str, Any]], None],
    ) -> None:
        self.per_coin = max(0, timeframes) * max(0, strategies)
        self._open: set[str] = set(symbols)
        self.total = len(self._open) * self.per_coin
        self._seen: dict[str, int] = {}
        self._done = 0
        self._emitted = -1
        self._emit = emit

    @property
    def done(self) -> int:
        return self._done

    def apply(self, message: object) -> bool:
        """Apply one worker message. Returns True when the done count moved."""
        if not isinstance(message, tuple) or len(message) != 2:
            return False
        kind, symbol = message
        if kind == STEP:
            return self._step(str(symbol))
        if kind == DONE:
            return self._finish(str(symbol))
        return False

    def drain(self, source: MessageSource) -> None:
        """Apply every message ready now, then emit once if the count moved."""
        moved = False
        while True:
            try:
                message = source.get_nowait()
            except queue.Empty:
                break
            moved = self.apply(message) or moved
        if moved:
            self.flush()

    def finish_coin(self, symbol: str) -> None:
        """Close a coin the parent gave up on (timeout); its unreported backtests count now."""
        if self._finish(symbol):
            self.flush()

    def in_process_sink(self) -> CallbackSink:
        """Sink for serial runs: each message is applied and emitted immediately."""

        def _on_message(message: object) -> None:
            if self.apply(message):
                self.flush()

        return CallbackSink(_on_message)

    def flush(self) -> None:
        """Emit the count, but only when it changed since the last emit."""
        if self._done == self._emitted:
            return
        self._emitted = self._done
        self._emit({"event": EVENT, "done": self._done, "total": self.total})

    def close(self) -> None:
        """Close every coin still open (crash, timeout, no report) and emit the final count."""
        for symbol in list(self._open):
            self._finish(symbol)
        self.flush()

    def _step(self, symbol: str) -> bool:
        if symbol not in self._open or self._seen.get(symbol, 0) >= self.per_coin:
            return False
        self._seen[symbol] = self._seen.get(symbol, 0) + 1
        self._done += 1
        return True

    def _finish(self, symbol: str) -> bool:
        if symbol not in self._open:
            return False
        self._open.discard(symbol)
        missing = self.per_coin - self._seen.pop(symbol, 0)
        self._done += missing
        return missing > 0
