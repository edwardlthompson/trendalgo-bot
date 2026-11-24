"""AV-G-STR2 — Windows toast kinds honor notify_prefs defaults."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.notify_prefs import NotifyPrefs, load_prefs, save_prefs


def test_default_windows_toast_kinds() -> None:
    prefs = NotifyPrefs()
    assert prefs.windows_logs is False
    assert prefs.windows_entered is True
    assert prefs.windows_left is True
    assert prefs.windows_trades is True


def test_load_prefs_windows_keys(tmp_path: Path) -> None:
    save_prefs(
        tmp_path,
        NotifyPrefs(
            windows_logs=True, windows_entered=False, windows_left=True, windows_trades=False
        ),
    )
    raw = json.loads((tmp_path / "notify_prefs.json").read_text(encoding="utf-8"))
    assert raw["windows_logs"] is True
    assert raw["windows_entered"] is False
    loaded = load_prefs(tmp_path)
    assert loaded.windows_logs is True
    assert loaded.windows_entered is False
    assert loaded.windows_trades is False
