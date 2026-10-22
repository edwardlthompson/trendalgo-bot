"""Alert preview helpers and kind-master prefs."""

from __future__ import annotations

from trendalgo.device.alert_preview import (
    SAMPLE_SYMBOL,
    kind_master_on,
    sample_event,
    set_kind_master,
    telegram_preview,
    windows_preview,
)
from trendalgo.device.notify_prefs import NotifyPrefs


def test_kind_master_round_trip() -> None:
    prefs = NotifyPrefs(
        windows_entered=False,
        telegram_entered=False,
        windows_left=True,
        telegram_left=False,
    )
    assert kind_master_on(prefs, "entered") is False
    assert kind_master_on(prefs, "left") is False
    on = set_kind_master(prefs, "entered", True)
    assert on.windows_entered is True
    assert on.telegram_entered is True
    assert kind_master_on(on, "entered") is True
    off = set_kind_master(on, "entered", False)
    assert kind_master_on(off, "entered") is False


def test_windows_and_telegram_preview_use_sample_symbol() -> None:
    for kind in ("entered", "left", "trades"):
        event = sample_event(kind)
        title, body = windows_preview(event)
        assert SAMPLE_SYMBOL in title or SAMPLE_SYMBOL in body or "BTC" in title
        assert body
        text = telegram_preview(event)
        assert SAMPLE_SYMBOL in text or "BTC" in text
        assert len(text) > 10
