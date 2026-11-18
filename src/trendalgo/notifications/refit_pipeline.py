"""Journal-first re-fit notification pipeline (NOTIF-01)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SinkResult:
    ok: bool
    detail: str
    sink: str = ""


class NotifySink(Protocol):
    name: str

    def send(self, title: str, body: str) -> SinkResult: ...


@dataclass
class NotifyResult:
    retune_completed: bool
    journaled: bool
    deliveries: list[SinkResult] = field(default_factory=list)


class RefitNotifyPipeline:
    """Delivery never blocks retune; journal write always happens first."""

    def __init__(
        self,
        *,
        journal_append: Callable[[dict[str, Any]], None],
        sinks: Sequence[NotifySink] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        max_attempts: int = 3,
        backoff_seconds: Sequence[float] = (0.5, 1.0, 2.0),
    ) -> None:
        self._journal_append = journal_append
        self._sinks = list(sinks or [])
        self._sleep = sleep_fn or (lambda _s: None)
        self._max_attempts = max(1, int(max_attempts))
        self._backoff = list(backoff_seconds)

    def notify_after_retune(
        self,
        *,
        event: str,
        title: str,
        body: str,
        retune_completed: bool,
        extra: dict[str, Any] | None = None,
    ) -> NotifyResult:
        entry: dict[str, Any] = {
            "ts": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "event": event,
            "title": title,
            "body": body,
            "retune_completed": retune_completed,
        }
        if extra:
            entry["extra"] = dict(extra)
        self._journal_append(entry)
        deliveries: list[SinkResult] = []
        for sink in self._sinks:
            deliveries.append(self._deliver_with_retry(sink, title, body))
        return NotifyResult(
            retune_completed=retune_completed,
            journaled=True,
            deliveries=deliveries,
        )

    def _deliver_with_retry(self, sink: NotifySink, title: str, body: str) -> SinkResult:
        last = SinkResult(ok=False, detail="no attempts", sink=sink.name)
        for attempt in range(self._max_attempts):
            try:
                result = sink.send(title, body)
                last = SinkResult(ok=result.ok, detail=result.detail, sink=sink.name)
            except Exception as exc:  # noqa: BLE001 — sink isolation
                last = SinkResult(ok=False, detail=str(exc), sink=sink.name)
            if last.ok:
                return last
            if attempt + 1 < self._max_attempts:
                delay = (
                    self._backoff[min(attempt, len(self._backoff) - 1)] if self._backoff else 0.0
                )
                self._sleep(float(delay))
        return last
