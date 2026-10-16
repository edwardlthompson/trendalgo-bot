"""Heartbeat and the missed-heartbeat alert (H5). The alert channel is injected: the owner picks it."""

from __future__ import annotations

from collections.abc import Callable

from trendalgo.botd.host_store import HostStore

DEFAULT_MAX_GAP_S = 300
MIN_MAX_GAP_S = 60


class Heartbeat:
    def __init__(self, store: HostStore, *, max_gap_s: int = DEFAULT_MAX_GAP_S) -> None:
        if max_gap_s < MIN_MAX_GAP_S:
            raise ValueError(f"max_gap_s must be at least {MIN_MAX_GAP_S}")
        self.store = store
        self.max_gap_s = max_gap_s

    def beat(self, now: int) -> None:
        with self.store.connect() as conn:
            conn.execute(
                "INSERT INTO heartbeat (id, beat_at) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET beat_at = excluded.beat_at",
                (now,),
            )

    def last_beat(self) -> int | None:
        with self.store.connect() as conn:
            row = conn.execute("SELECT beat_at FROM heartbeat WHERE id = 1").fetchone()
        return int(row["beat_at"]) if row is not None else None

    def check(self, now: int, *, started_at: int, notify: Callable[[str], None]) -> bool:
        """Send one alert if the host has been silent longer than max_gap_s. True when it alerted.

        A host that has never beaten is measured from its start time, so a host that never comes
        up still raises the alert. The caller sets how often this runs.
        """
        last = self.last_beat()
        reference = started_at if last is None else last
        silent_for = now - reference
        if silent_for <= self.max_gap_s:
            return False
        notify(f"TrendAlgo host silent for {silent_for} s (limit {self.max_gap_s} s)")
        return True
