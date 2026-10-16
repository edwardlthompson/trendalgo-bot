"""H2/H3: the go-live CLI signs approvals and writes the audit line only after the host accepts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trendalgo.trading import go_live_cli
from trendalgo.trading.signed_command import SignedNonceStore, verify_request

OWNER = "owner-cli"
SECRET = "owner-secret-for-cli-tests"


@pytest.fixture
def owner_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("TRENDALGO_OWNER_ID", OWNER)
    monkeypatch.setenv("TRENDALGO_OWNER_SECRET", SECRET)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_signed_headers_verify_on_the_host_for_the_same_path(tmp_path: Path) -> None:
    path = go_live_cli.go_live_path("kraken")
    headers = go_live_cli.signed_headers(
        "kraken", owner_id=OWNER, secret=SECRET, timestamp=1_800_000_000, nonce="cli-nonce-0000001"
    )
    verdict = verify_request(
        method="POST",
        path=path,
        body=b"",
        headers=headers,
        secret=SECRET,
        owner_id=OWNER,
        nonce_store=SignedNonceStore(tmp_path / "nonces.db"),
        now=1_800_000_000,
    )
    assert verdict.ok, verdict.reason


def test_no_audit_line_is_written_when_the_host_refuses(
    owner_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(go_live_cli, "post_go_live", lambda *_a, **_k: 403)
    assert go_live_cli.main(["--exchange", "kraken"]) == 1
    assert not (owner_env / "data" / "audit" / "go-live.jsonl").exists()


def test_an_audit_line_is_written_only_after_the_host_accepts(
    owner_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(go_live_cli, "post_go_live", lambda *_a, **_k: 200)
    assert go_live_cli.main(["--exchange", "kraken"]) == 0
    lines = (owner_env / "data" / "audit" / "go-live.jsonl").read_text(encoding="utf-8")
    record = json.loads(lines.strip())
    assert record["exchange"] == "kraken"
    assert record["signed"] is True
    assert record["gate"] == "H-010/H-028"


def test_the_cli_refuses_to_run_without_the_owner_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TRENDALGO_OWNER_ID", raising=False)
    monkeypatch.delenv("TRENDALGO_OWNER_SECRET", raising=False)
    monkeypatch.chdir(tmp_path)
    assert go_live_cli.main(["--exchange", "kraken"]) == 2
    assert not (tmp_path / "data" / "audit" / "go-live.jsonl").exists()
