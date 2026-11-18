"""Device Grok Bot test helper — no Qt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.device.grokbot_notify import grokbot_status_line, send_device_test


def test_status_off_by_default() -> None:
    assert grokbot_status_line() == "off"


def test_send_device_test_not_configured() -> None:
    ok, detail = send_device_test()
    assert ok is False
    assert detail == "not_configured"


def test_status_and_test_use_host_when_local_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Resp:
        ok = True
        data: dict[str, Any] = {"enabled": True, "sent": True}

    class _Client:
        def get_grokbot_status(self) -> _Resp:
            return _Resp()

        def post_grokbot_test(self) -> _Resp:
            return _Resp()

    monkeypatch.setattr(
        "trendalgo.device.grokbot_notify.try_open_host_client",
        lambda _path: _Client(),
    )
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    assert grokbot_status_line(settings) == "on"
    ok, detail = send_device_test(settings)
    assert ok is True
    assert detail == "sent"
