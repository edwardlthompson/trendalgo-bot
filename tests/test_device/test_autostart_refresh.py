"""Autostart Run key rewrite when start-with-Windows is on."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trendalgo.device import autostart


@pytest.mark.skipif(autostart.sys.platform != "win32", reason="Windows registry only")
def test_set_enabled_true_rewrites_default_command() -> None:
    key = MagicMock()
    key.__enter__ = MagicMock(return_value=key)
    key.__exit__ = MagicMock(return_value=False)
    with (
        patch("winreg.CreateKeyEx", return_value=key),
        patch("winreg.SetValueEx") as set_value,
        patch.object(
            autostart,
            "default_command",
            return_value=r'"C:\py\pythonw.exe" -m trendalgo.device',
        ),
    ):
        autostart.set_enabled(True)
    set_value.assert_called_once()
    _key, name, _reserved, _typ, cmd = set_value.call_args[0]
    assert name == autostart.VALUE_NAME
    assert "trendalgo.device" in cmd
