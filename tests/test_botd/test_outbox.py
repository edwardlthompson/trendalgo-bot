"""ADR-0016 outbox: owner-checked, dedupe-keyed, pulled by the device and acknowledged."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.botd.host_store import HostStore
from trendalgo.botd.outbox import Outbox
from trendalgo.botd.owner import ForeignOwnerError

HOST = "owner-host-1"
NOW = 1_800_000_000


def _outbox(tmp_path: Path) -> Outbox:
    return Outbox(HostStore(tmp_path / "host.db"), host_owner_id=HOST)


def _queue(outbox: Outbox, key: str, *, payload: dict[str, object] | None = None) -> bool:
    return outbox.enqueue(
        owner_id=HOST,
        dedupe_key=key,
        kind="fill",
        payload=payload or {"qty": 1},
        now=NOW,
    )


def test_queued_events_come_back_in_order_with_their_payload(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    _queue(outbox, "fill-1", payload={"qty": 0.5, "pair": "BTC/USD"})
    _queue(outbox, "fill-2")
    events = outbox.pending()
    assert [event["payload"] for event in events] == [{"qty": 0.5, "pair": "BTC/USD"}, {"qty": 1}]
    assert all(event["kind"] == "fill" and event["created_at"] == NOW for event in events)


def test_a_repeated_dedupe_key_is_ignored_so_a_retry_is_harmless(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    assert _queue(outbox, "fill-1") is True
    assert _queue(outbox, "fill-1") is False
    assert len(outbox.pending()) == 1


def test_a_foreign_or_missing_owner_is_refused(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    with pytest.raises(ForeignOwnerError):
        outbox.enqueue(owner_id="owner-2", dedupe_key="k", kind="fill", payload={}, now=NOW)
    with pytest.raises(ForeignOwnerError):
        outbox.enqueue(owner_id=None, dedupe_key="k", kind="fill", payload={}, now=NOW)
    assert outbox.pending() == []


def test_a_dedupe_key_and_a_kind_are_required(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    with pytest.raises(ValueError, match="required"):
        outbox.enqueue(owner_id=HOST, dedupe_key="", kind="fill", payload={}, now=NOW)
    with pytest.raises(ValueError, match="required"):
        outbox.enqueue(owner_id=HOST, dedupe_key="k", kind="", payload={}, now=NOW)


def test_ack_removes_only_the_listed_events(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    for key in ("a", "b", "c"):
        _queue(outbox, key)
    first, second, third = (event["id"] for event in outbox.pending())
    assert outbox.ack([first, third]) == 2
    assert [event["id"] for event in outbox.pending()] == [second]


def test_ack_ignores_unknown_ids_and_an_empty_list(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    _queue(outbox, "a")
    assert outbox.ack([999]) == 0
    assert outbox.ack([]) == 0
    assert len(outbox.pending()) == 1


def test_pending_respects_the_limit(tmp_path: Path) -> None:
    outbox = _outbox(tmp_path)
    for index in range(5):
        _queue(outbox, f"event-{index}")
    assert len(outbox.pending(limit=2)) == 2
