"""AV-G-STR3 — startup surface exposes crash + prompt ack helpers."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.crash_capture.pending_crash import persist_pending_crash
from trendalgo.results_store.desk_startup import ack_startup_prompt, load_startup_surface


def test_startup_surface_includes_pending_crash(tmp_path: Path) -> None:
    persist_pending_crash(
        tmp_path,
        {"message": "boom", "stack": "trace"},
        save_local=True,
    )
    payload = load_startup_surface(tmp_path, skip_network=True)
    assert payload["crash"] is not None
    assert "boom" in payload["crash"]["message"]
    assert payload["prompt"] is None
    assert "crash_clear" in payload["copy"]


def test_ack_clear_crash(tmp_path: Path) -> None:
    persist_pending_crash(
        tmp_path,
        {"message": "boom", "stack": "trace"},
        save_local=True,
    )
    assert (tmp_path / "pending_crash.json").exists()
    out = ack_startup_prompt(tmp_path, kind="clear_crash")
    assert out["ok"] is True
    assert not (tmp_path / "pending_crash.json").exists()


def test_ack_donate_marks_version(tmp_path: Path) -> None:
    out = ack_startup_prompt(tmp_path, kind="donate", current_version="1.2.3")
    assert out["ok"] is True
    prefs = json.loads((tmp_path / "update_prefs.json").read_text(encoding="utf-8"))
    assert prefs["last_seen_version"] == "1.2.3"
