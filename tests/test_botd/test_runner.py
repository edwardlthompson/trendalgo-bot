"""PlanRunner tick announces a plan once and heartbeats."""

from __future__ import annotations

from pathlib import Path

from trendalgo.botd.host_store import HostStore
from trendalgo.botd.outbox import Outbox
from trendalgo.botd.runner import PlanRunner


def test_runner_tick_announces_plan_once(tmp_path: Path) -> None:
    store = HostStore(tmp_path / "host.db")
    store.save_plan(plan_version=1, bundle_hash="a" * 64, body='{"bots":[{"id":"1"}]}')
    runner = PlanRunner(store, host_owner_id="owner-1", shadow=True, clock=lambda: 100)
    first = runner.tick()
    assert first["plan_version"] == 1
    second = runner.tick()
    assert second["plan_version"] == 1
    events = Outbox(store, host_owner_id="owner-1").pending()
    started = [event for event in events if event["kind"] == "runner_started"]
    assert len(started) == 1
    assert started[0]["payload"]["shadow"] is True


def test_runner_run_forever_respects_iterations(tmp_path: Path) -> None:
    store = HostStore(tmp_path / "host.db")
    sleeps: list[float] = []
    runner = PlanRunner(
        store,
        host_owner_id="owner-1",
        sleep=sleeps.append,
        clock=lambda: 1,
    )
    runner.run_forever(interval_s=5.0, iterations=2)
    assert len(sleeps) == 1
