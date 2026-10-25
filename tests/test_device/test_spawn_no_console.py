"""Spawn workers must not flash console windows on Windows GUI launches."""

from __future__ import annotations

import sys

import pytest

from trendalgo.device.spawn_no_console import install_spawn_no_console


def test_install_spawn_no_console_idempotent() -> None:
    first = install_spawn_no_console()
    second = install_spawn_no_console()
    if sys.platform == "win32":
        assert first is True
        assert second is True
    else:
        assert first is False
        assert second is False


@pytest.mark.skipif(sys.platform != "win32", reason="win32 CreateProcess patch")
def test_spawn_popen_is_patched() -> None:
    install_spawn_no_console()
    from multiprocessing import popen_spawn_win32 as psw

    assert psw.Popen.__init__.__name__ == "_init"
