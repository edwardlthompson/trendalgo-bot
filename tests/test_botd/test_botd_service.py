"""Composition root: the host refuses to start without its owner config, and `pair` issues a code."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendalgo.botd.host_store import HostStore
from trendalgo.botd.pairing import PairingCodes
from trendalgo.botd.service import build_app, main
from trendalgo.trading.signed_command import now_seconds

SECRET = "owner-secret-for-tests-only"


def _env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, owner: str | None, secret: str | None
) -> None:
    for name, value in (("TRENDALGO_OWNER_ID", owner), ("TRENDALGO_OWNER_SECRET", secret)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    monkeypatch.setenv("TRENDALGO_BOTD_DIR", str(tmp_path / "botd"))


def test_the_host_refuses_to_start_without_its_owner_id_and_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _env(monkeypatch, tmp_path, owner="owner-1", secret=None)
    with pytest.raises(RuntimeError, match="must be set"):
        build_app()
    _env(monkeypatch, tmp_path, owner=None, secret=SECRET)
    with pytest.raises(RuntimeError, match="must be set"):
        build_app()


def test_the_app_keeps_its_database_in_the_host_folder_and_stays_owner_gated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _env(monkeypatch, tmp_path, owner="owner-1", secret=SECRET)
    client = TestClient(build_app())
    assert client.get("/api/v1/status").status_code == 403
    assert (tmp_path / "botd" / "host.db").is_file()


def test_pair_prints_a_code_that_redeems_exactly_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _env(monkeypatch, tmp_path, owner="owner-1", secret=SECRET)
    assert main(["pair"]) == 0
    code = capsys.readouterr().out.strip().rsplit(": ", 1)[-1]
    codes = PairingCodes(HostStore(tmp_path / "botd" / "host.db"))
    assert codes.redeem(code, now_seconds()) is True
    assert codes.redeem(code, now_seconds()) is False


def test_an_unknown_command_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["serve"]) == 2
    assert "usage" in capsys.readouterr().err
