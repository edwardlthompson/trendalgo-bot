"""Entry points: the self-test, the argument routing, and the database switch at startup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from trendalgo.device import __main__ as device_main
from trendalgo.device import strings as S
from trendalgo.device.app import prepare_databases
from trendalgo.device.context import DeviceContext
from trendalgo.device.selftest import run_selftest


def test_the_selftest_passes_on_this_machine(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_selftest(include_window=False) == 0
    out = capsys.readouterr().out
    assert "OK workers" in out
    assert "OK wal" in out
    assert "OK lock" in out
    assert "OK talib" in out
    assert "window" not in out


def test_the_selftest_fails_when_talib_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("trendalgo.device.selftest.talib_available", lambda: False)
    assert run_selftest(include_window=False) == 1
    assert "FAIL talib" in capsys.readouterr().out


def test_the_selftest_flag_returns_its_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("trendalgo.device.selftest.run_selftest", lambda: 7)
    assert device_main.main(["--selftest"]) == 7


def test_without_the_flag_the_window_entry_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []

    def _detach(*, testing: bool = False) -> bool:
        called.append(testing)
        return True

    monkeypatch.setattr("trendalgo.device.console_detach.detach_console_if_needed", _detach)
    monkeypatch.setattr("trendalgo.device.app.run", lambda: 5)
    assert device_main.main([]) == 5
    assert called == [False]


def test_should_detach_console_skips_testing_and_keep_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trendalgo.device.console_detach import should_detach_console

    monkeypatch.setattr(device_main.sys, "platform", "win32")
    assert should_detach_console(testing=True) is False
    monkeypatch.setenv("TRENDALGO_KEEP_CONSOLE", "1")
    assert should_detach_console(testing=False) is False
    monkeypatch.delenv("TRENDALGO_KEEP_CONSOLE", raising=False)
    assert should_detach_console(testing=False) is True


def test_prepare_databases_switches_existing_device_files_only(ctx: DeviceContext) -> None:
    scanner = ctx.databases["scanner"]
    sqlite3.connect(scanner).close()
    assert prepare_databases(ctx) == []
    with sqlite3.connect(scanner) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert not ctx.databases["bots"].exists()


def test_prepare_databases_reports_a_file_it_cannot_switch(ctx: DeviceContext) -> None:
    path: Path = ctx.databases["bots"]
    path.write_bytes(b"x" * 4096)
    assert prepare_databases(ctx) == [S.WAL_NOTICE.format(name="bots.db")]
