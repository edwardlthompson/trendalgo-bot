"""Device Grok Bot test helper — no Qt."""

from __future__ import annotations

from trendalgo.device.grokbot_notify import grokbot_status_line, send_device_test


def test_status_off_by_default() -> None:
    assert grokbot_status_line() == "off"


def test_send_device_test_not_configured() -> None:
    ok, detail = send_device_test()
    assert ok is False
    assert detail == "not_configured"
