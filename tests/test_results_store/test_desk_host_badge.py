"""AV-G-OTH4 — global host badge surface."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.profile import SETTINGS_FILE
from trendalgo.results_store.desk_host_badge import load_host_badge_surface


def test_host_badge_local_without_settings(tmp_path: Path) -> None:
    data = load_host_badge_surface(tmp_path)
    assert data["ok"] is True
    assert data["linked"] is False
    assert data["host_badge"] == "local"
    assert data["label"]


def test_host_badge_needs_secret_even_with_host(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_WIZARD_MEMORY", "1")
    (tmp_path / SETTINGS_FILE).write_text(
        '{"owner_id":"desk","host_url":"http://127.0.0.1:8765","theme":"system","accent":""}',
        encoding="utf-8",
    )
    data = load_host_badge_surface(tmp_path)
    assert data["linked"] is False
    assert data["host_url"].startswith("http://127.0.0.1")
