"""ADR-0016 host store: one SQLite file for plan, positions, outbox, heartbeat and pairing codes."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.botd.host_store import HostStore, StalePlanError


def _store(tmp_path: Path) -> HostStore:
    return HostStore(tmp_path / "host.db")


def test_a_new_store_holds_no_plan_and_no_positions(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.plan() is None
    assert store.positions() == {}


def test_a_saved_plan_reads_back_unchanged(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_plan(plan_version=1, bundle_hash="h1", body='{"bots":[]}')
    assert store.plan() == {"plan_version": 1, "bundle_hash": "h1", "body": '{"bots":[]}'}


def test_a_newer_plan_replaces_the_stored_one(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_plan(plan_version=1, bundle_hash="h1", body="{}")
    store.save_plan(plan_version=2, bundle_hash="h2", body='{"v":2}')
    plan = store.plan()
    assert plan is not None
    assert (plan["plan_version"], plan["bundle_hash"]) == (2, "h2")


def test_an_equal_or_older_plan_is_refused_and_the_stored_plan_kept(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_plan(plan_version=2, bundle_hash="h2", body="{}")
    with pytest.raises(StalePlanError):
        store.save_plan(plan_version=2, bundle_hash="other", body="{}")
    with pytest.raises(StalePlanError):
        store.save_plan(plan_version=1, bundle_hash="h1", body="{}")
    plan = store.plan()
    assert plan is not None
    assert (plan["plan_version"], plan["bundle_hash"]) == (2, "h2")


def test_positions_are_upserted_per_bot(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save_position("bot-2", '{"qty":0.5}')
    store.save_position("bot-1", '{"qty":1.0}')
    store.save_position("bot-1", '{"qty":1.5}')
    assert store.positions() == {"bot-1": '{"qty":1.5}', "bot-2": '{"qty":0.5}'}


def test_reopening_the_file_keeps_plan_and_positions(tmp_path: Path) -> None:
    first = _store(tmp_path)
    first.save_plan(plan_version=3, bundle_hash="h3", body="{}")
    first.save_position("bot-1", '{"qty":2}')
    reopened = HostStore(tmp_path / "host.db")
    plan = reopened.plan()
    assert plan is not None and plan["plan_version"] == 3
    assert reopened.positions() == {"bot-1": '{"qty":2}'}
