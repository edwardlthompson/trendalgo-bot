"""Host plan runner (shadow-first): loads the approved plan and emits heartbeat events.

Full LTS StreamingTrader wiring lands with live go-live. This loop proves the host
keeps a beat and records runner_started events when a plan is present.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from trendalgo.botd.heartbeat import Heartbeat
from trendalgo.botd.host_store import HostStore
from trendalgo.botd.outbox import Outbox

log = logging.getLogger(__name__)


class PlanRunner:
    def __init__(
        self,
        store: HostStore,
        *,
        host_owner_id: str,
        shadow: bool = True,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], int] = lambda: int(time.time()),
    ) -> None:
        self.store = store
        self.host_owner_id = host_owner_id
        self.shadow = shadow
        self._sleep = sleep
        self._clock = clock
        self._heartbeat = Heartbeat(store)
        self._outbox = Outbox(store, host_owner_id=host_owner_id)
        self._announced_version: int | None = None

    def tick(self) -> dict[str, Any]:
        """One iteration: beat, announce plan once, return a small status dict."""
        now = self._clock()
        self._heartbeat.beat(now)
        plan = self.store.plan()
        version = int(plan["plan_version"]) if plan else 0
        if plan and version != self._announced_version:
            bots = _bot_count(str(plan.get("body") or ""))
            self._outbox.enqueue(
                owner_id=self.host_owner_id,
                dedupe_key=f"runner:plan:{version}",
                kind="runner_started",
                payload={
                    "plan_version": version,
                    "bots": bots,
                    "shadow": self.shadow,
                },
                now=now,
            )
            self._announced_version = version
            log.info(
                "runner announced plan_version=%s shadow=%s bots=%s", version, self.shadow, bots
            )
        return {"plan_version": version, "shadow": self.shadow, "beat_at": now}

    def run_forever(self, *, interval_s: float = 30.0, iterations: int | None = None) -> None:
        """Loop ticks. `iterations` limits the loop for tests; None runs until stopped."""
        count = 0
        while iterations is None or count < iterations:
            self.tick()
            count += 1
            if iterations is not None and count >= iterations:
                break
            self._sleep(interval_s)


def _bot_count(body: str) -> int:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 0
    bots = payload.get("bots") if isinstance(payload, dict) else None
    return len(bots) if isinstance(bots, list) else 0
