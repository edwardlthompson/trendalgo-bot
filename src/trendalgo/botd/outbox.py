"""Outbox for device-bound events (ADR-0016). The device pulls, then acks; dedupe keys make retries safe."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from trendalgo.botd.host_store import HostStore
from trendalgo.botd.owner import assert_owner


class Outbox:
    def __init__(self, store: HostStore, *, host_owner_id: str) -> None:
        self.store = store
        self.host_owner_id = host_owner_id

    def enqueue(
        self,
        *,
        owner_id: str | None,
        dedupe_key: str,
        kind: str,
        payload: dict[str, Any],
        now: int,
    ) -> bool:
        """Queue one event. False when the dedupe key is already queued, so a retry is harmless."""
        assert_owner(owner_id, self.host_owner_id)
        if not dedupe_key or not kind:
            raise ValueError("dedupe_key and kind are required")
        with self.store.connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO outbox (dedupe_key, kind, payload, created_at) "
                "VALUES (?, ?, ?, ?)",
                (dedupe_key, kind, json.dumps(payload, sort_keys=True), now),
            )
            return cur.rowcount == 1

    def pending(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.store.connect() as conn:
            rows = conn.execute(
                "SELECT id, kind, payload, created_at FROM outbox ORDER BY id LIMIT ?", (limit,)
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "kind": str(row["kind"]),
                "payload": json.loads(row["payload"]),
                "created_at": int(row["created_at"]),
            }
            for row in rows
        ]

    def ack(self, ids: Iterable[int]) -> int:
        """Delete acknowledged events. Unknown ids are ignored. Returns how many were removed."""
        wanted = [int(event_id) for event_id in ids]
        if not wanted:
            return 0
        marks = ",".join("?" for _ in wanted)
        with self.store.connect() as conn:
            cur = conn.execute(f"DELETE FROM outbox WHERE id IN ({marks})", wanted)
            return cur.rowcount
