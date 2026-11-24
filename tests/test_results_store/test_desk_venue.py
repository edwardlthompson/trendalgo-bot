"""AV-G-SET1 — execution venue surface + apply."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.execution_venue import load_execution_venue
from trendalgo.results_store.desk_venue import apply_execution_venue, load_execution_venue_surface


def test_venue_surface_defaults(tmp_path: Path) -> None:
    data = load_execution_venue_surface(tmp_path)
    assert data["venue"] == "host"
    assert data["disclosure_accepted"] is False
    assert data["disclosure_text"]
    assert {c["id"] for c in data["choices"]} == {"host", "device"}


def test_venue_apply_device_requires_ack(tmp_path: Path) -> None:
    bad = apply_execution_venue(tmp_path, {"venue": "device", "disclosure_accepted": False})
    assert bad["ok"] is False
    ok = apply_execution_venue(tmp_path, {"venue": "device", "disclosure_accepted": True})
    assert ok["ok"] is True
    assert load_execution_venue(tmp_path).venue == "device"
    assert load_execution_venue(tmp_path).disclosure_accepted is True
