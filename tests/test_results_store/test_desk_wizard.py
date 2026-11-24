"""AV-G-SET6 — setup wizard W0–W5 desk surface."""

from __future__ import annotations

import os
from pathlib import Path

from trendalgo.device.wizard.content import STEPS
from trendalgo.results_store.desk_wizard import (
    advance_wizard,
    load_wizard_surface,
    rewind_wizard,
)


def test_wizard_surface_starts_at_w0(tmp_path: Path) -> None:
    data = load_wizard_surface(tmp_path)
    assert data["ok"] is True
    assert data["step_id"] == "W0"
    assert data["kind"] == "ack"
    assert data["number"] == 1
    assert data["total"] == 6
    assert len(data["body"]) == len(STEPS[0].body)


def test_wizard_advance_w0_requires_ack(tmp_path: Path) -> None:
    blocked = advance_wizard(tmp_path, {"ack": False})
    assert blocked["ok"] is False
    assert blocked["error"] == "validation"
    ok = advance_wizard(tmp_path, {"ack": True})
    assert ok["ok"] is True
    assert ok["step_id"] == "W1"
    assert ok["kind"] == "keys"
    assert ok["done"] == ["W0"]


def test_wizard_rewind(tmp_path: Path) -> None:
    advance_wizard(tmp_path, {"ack": True})
    back = rewind_wizard(tmp_path)
    assert back["ok"] is True
    assert back["step_id"] == "W0"
    assert back["done"] == []


def test_wizard_w1_permissions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_WIZARD_MEMORY", "1")
    advance_wizard(tmp_path, {"ack": True})
    from trendalgo.device.wizard.validators import PERMISSIONS

    bad = advance_wizard(tmp_path, {"permissions": [], "withdraw_off": True})
    assert bad["ok"] is False
    good = advance_wizard(
        tmp_path,
        {"permissions": list(PERMISSIONS), "withdraw_off": True},
    )
    assert good["ok"] is True
    assert good["step_id"] == "W2"
    assert "W1" in good["done"]
    # Ensure env does not leak to other tests that might run practice.
    os.environ.pop("TRENDALGO_WIZARD_MEMORY", None)
