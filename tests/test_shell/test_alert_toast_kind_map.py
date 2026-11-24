"""AV-G-ALR2 — alert event kinds map onto notify_prefs Windows gates."""

from __future__ import annotations

from trendalgo.device.alert_preview import KINDS, kind_master_on, sample_event, windows_preview
from trendalgo.device.notify_prefs import NotifyPrefs


def test_sample_windows_preview_for_ribbon_kinds() -> None:
    prefs = NotifyPrefs()
    for kind in KINDS:
        assert kind_master_on(prefs, kind) is True
        title, body = windows_preview(sample_event(kind))
        assert title
        assert body


def test_disabled_entered_blocks_master() -> None:
    prefs = NotifyPrefs(windows_entered=False, telegram_entered=False)
    assert kind_master_on(prefs, "entered") is False
