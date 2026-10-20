"""Device vs host venue disclosure (Phase 3)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.execution_venue import (
    ExecutionVenueSettings,
    load_execution_venue,
    save_execution_venue,
)
from trendalgo.device.local_runner import device_tick_allowed


def test_venue_persists_once(tmp_path: Path) -> None:
    save_execution_venue(
        tmp_path,
        ExecutionVenueSettings(venue="device", disclosure_accepted=True),
    )
    loaded = load_execution_venue(tmp_path)
    assert loaded.venue == "device"
    assert loaded.disclosure_accepted is True


def test_device_tick_requires_disclosure_and_go_live() -> None:
    blocked = device_tick_allowed(
        venue="device",
        disclosure_accepted=False,
        dry_run=True,
        go_live_approved=False,
        credentials_ok=True,
        paused=False,
    )
    assert blocked.blocked == "disclosure_required"
    dry = device_tick_allowed(
        venue="device",
        disclosure_accepted=True,
        dry_run=True,
        go_live_approved=False,
        credentials_ok=True,
        paused=False,
    )
    assert dry.mode == "dry_run"
    live_blocked = device_tick_allowed(
        venue="device",
        disclosure_accepted=True,
        dry_run=False,
        go_live_approved=False,
        credentials_ok=True,
        paused=False,
    )
    assert live_blocked.blocked == "go_live_required"
    live_ok = device_tick_allowed(
        venue="device",
        disclosure_accepted=True,
        dry_run=False,
        go_live_approved=True,
        credentials_ok=True,
        paused=False,
    )
    assert live_ok.mode == "live_approved"
