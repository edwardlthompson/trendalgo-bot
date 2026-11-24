"""AV-G-SET4 — connection owner/host/cert surface + apply."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.profile import SETTINGS_FILE, read_json
from trendalgo.results_store.desk_connection import (
    apply_connection_settings,
    load_connection_surface,
)


def test_connection_surface_first_run(tmp_path: Path) -> None:
    data = load_connection_surface(tmp_path)
    assert data["ok"] is True
    assert data["first_run"] is True
    assert data["owner_id"] == ""
    assert data["help"]


def test_apply_connection_settings_roundtrip(tmp_path: Path) -> None:
    # Seed appearance fields that must survive connection save.
    (tmp_path / SETTINGS_FILE).write_text(
        '{"owner_id":"seed","theme":"dark","accent":"#2563eb","use_utc":true}',
        encoding="utf-8",
    )
    result = apply_connection_settings(
        tmp_path,
        {
            "owner_id": "desk-owner",
            "host_url": "https://host.example:8443",
            "cert_sha256": "a" * 64,
        },
    )
    assert result["ok"] is True
    assert result["owner_id"] == "desk-owner"
    doc = read_json(tmp_path / SETTINGS_FILE)
    assert doc is not None
    assert doc["owner_id"] == "desk-owner"
    assert doc["host_url"] == "https://host.example:8443"
    assert doc["cert_sha256"] == "a" * 64
    assert doc["theme"] == "dark"
    assert doc["accent"] == "#2563eb"
    assert doc["use_utc"] is True
    loaded = load_connection_surface(tmp_path)
    assert loaded["first_run"] is False
    assert loaded["owner_id"] == "desk-owner"


def test_apply_connection_rejects_bad_owner(tmp_path: Path) -> None:
    result = apply_connection_settings(tmp_path, {"owner_id": "bad owner!"})
    assert result["ok"] is False
    assert result["error"] == "validation"
    assert result["problems"]
