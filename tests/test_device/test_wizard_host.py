"""The device's signed calls and practice mode, against the real host API on 127.0.0.1."""

from __future__ import annotations

import secrets
import socket
import sqlite3
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn

from trendalgo.device.wizard.credentials import (
    OWNER_SECRET_TARGET,
    PRACTICE_SECRET_TARGET,
    CredentialError,
    MemoryCredentialStore,
)
from trendalgo.device.wizard.hostclient import (
    STATUS_PATH,
    UNREACHABLE,
    HostClient,
    HostRefusedError,
    pair_host,
)
from trendalgo.device.wizard.practice import (
    PRACTICE_OWNER_ID,
    PracticeHost,
    _run_checks,
    run_practice,
)


def _closed_loopback_url() -> str:
    """A loopback address with nothing listening: bind, read the port, close again."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    return f"http://127.0.0.1:{port}"


@pytest.fixture
def host(tmp_path: Path) -> Iterator[tuple[PracticeHost, str]]:
    secret = secrets.token_urlsafe(32)
    with PracticeHost(tmp_path, secret) as running:
        yield running, secret


def test_the_client_refuses_a_real_host_before_any_request() -> None:
    with pytest.raises(HostRefusedError) as info:
        HostClient("https://host.example:8443", PRACTICE_OWNER_ID, "x" * 32)
    assert info.value.problem.code == "host.not_loopback"


def test_a_closed_port_reports_unreachable_instead_of_raising() -> None:
    client = HostClient(_closed_loopback_url(), PRACTICE_OWNER_ID, "x" * 32)
    assert client.call("GET", STATUS_PATH) == UNREACHABLE


def test_a_reply_that_is_not_http_reports_unreachable_instead_of_raising() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = int(listener.getsockname()[1])

    def answer_with_garbage() -> None:
        conn, _ = listener.accept()
        with conn:
            conn.recv(65536)
            conn.sendall(b"NOT HTTP AT ALL\r\n\r\n")

    thread = threading.Thread(target=answer_with_garbage, daemon=True)
    thread.start()
    try:
        client = HostClient(f"http://127.0.0.1:{port}", PRACTICE_OWNER_ID, "x" * 32)
        assert client.call("GET", STATUS_PATH) == UNREACHABLE
    finally:
        thread.join(timeout=5)
        listener.close()


def test_a_database_error_while_starting_is_reported_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_database(self: PracticeHost) -> PracticeHost:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(PracticeHost, "__enter__", broken_database)
    problems = run_practice(tmp_path, MemoryCredentialStore())
    assert [problem.code for problem in problems] == ["practice.host_failed"]


def test_the_practice_host_is_bound_to_loopback_and_refuses_unsigned_calls(
    host: tuple[PracticeHost, str],
) -> None:
    running, _ = host
    assert running.base_url.startswith("http://127.0.0.1:")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with pytest.raises(urllib.error.HTTPError) as info:
        opener.open(running.base_url + STATUS_PATH, timeout=5)
    assert info.value.code == 403


def test_the_practice_checks_pass_on_the_real_host(tmp_path: Path) -> None:
    store = MemoryCredentialStore()
    assert run_practice(tmp_path, store) == []
    secret = store.read(PRACTICE_SECRET_TARGET)
    assert secret is not None
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes(), f"secret written to {path.name}"


def test_a_second_practice_run_reuses_the_same_secret(tmp_path: Path) -> None:
    store = MemoryCredentialStore()
    assert run_practice(tmp_path, store) == []
    first = store.read(PRACTICE_SECRET_TARGET)
    assert run_practice(tmp_path, store) == []
    assert store.read(PRACTICE_SECRET_TARGET) == first


def test_a_host_that_cannot_start_is_reported_as_a_problem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse_to_start(self: PracticeHost) -> PracticeHost:
        raise RuntimeError("the host did not start on 127.0.0.1")

    monkeypatch.setattr(PracticeHost, "__enter__", refuse_to_start)
    problems = run_practice(tmp_path, MemoryCredentialStore())
    assert [problem.code for problem in problems] == ["practice.host_failed"]


def test_a_server_thread_that_exits_at_once_is_reported_as_a_start_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(uvicorn.Server, "run", lambda self: None)
    problems = run_practice(tmp_path, MemoryCredentialStore())
    assert [problem.code for problem in problems] == ["practice.host_failed"]


def test_a_vault_refusal_is_reported_as_a_problem_not_raised(tmp_path: Path) -> None:
    class BrokenVault(MemoryCredentialStore):
        def read(self, target: str) -> str | None:
            raise CredentialError("Credential Manager could not read it (Windows error 5).")

    problems = run_practice(tmp_path, BrokenVault())
    assert [problem.code for problem in problems] == ["practice.vault"]


def test_issuing_a_code_needs_a_running_host(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not running"):
        PracticeHost(tmp_path, "x" * 32).issue_code()


class _FakeClient:
    def __init__(self, status: int) -> None:
        self._status = status

    def call(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        secret: str | None = None,
    ) -> int:
        return self._status


class _FakeHost:
    def issue_code(self) -> str:
        return "ABCD-EFGH"


def test_a_host_that_accepts_a_forged_call_or_a_reused_code_fails_the_checks() -> None:
    problems = _run_checks(_FakeClient(200), _FakeHost(), "s" * 32)  # type: ignore[arg-type]
    assert [problem.code for problem in problems] == [
        "practice.forgery_accepted",
        "practice.reuse_accepted",
    ]


def test_a_host_that_refuses_the_status_call_stops_at_the_pairing_step() -> None:
    problems = _run_checks(_FakeClient(403), _FakeHost(), "s" * 32)  # type: ignore[arg-type]
    assert [problem.code for problem in problems] == [
        "practice.status_refused",
        "practice.pair_refused",
    ]


def test_pairing_with_the_practice_host_saves_the_owner_secret(
    host: tuple[PracticeHost, str],
) -> None:
    running, secret = host
    store = MemoryCredentialStore()
    code = running.issue_code()
    assert pair_host(running.base_url, PRACTICE_OWNER_ID, secret, code, store) == []
    assert store.read(OWNER_SECRET_TARGET) == secret


def test_a_pairing_code_works_once(host: tuple[PracticeHost, str]) -> None:
    running, secret = host
    code = running.issue_code()
    assert (
        pair_host(running.base_url, PRACTICE_OWNER_ID, secret, code, MemoryCredentialStore()) == []
    )
    again = pair_host(running.base_url, PRACTICE_OWNER_ID, secret, code, MemoryCredentialStore())
    assert [problem.code for problem in again] == ["pair.code_refused"]


def test_an_unknown_code_is_refused(host: tuple[PracticeHost, str]) -> None:
    running, secret = host
    store = MemoryCredentialStore()
    problems = pair_host(running.base_url, PRACTICE_OWNER_ID, secret, "ABCD-EFGH", store)
    assert [problem.code for problem in problems] == ["pair.code_refused"]
    assert store.read(OWNER_SECRET_TARGET) is None


def test_a_wrong_owner_secret_is_refused_and_the_code_is_not_spent(
    host: tuple[PracticeHost, str],
) -> None:
    running, secret = host
    store = MemoryCredentialStore()
    code = running.issue_code()
    problems = pair_host(running.base_url, PRACTICE_OWNER_ID, "y" * 32, code, store)
    assert [problem.code for problem in problems] == ["owner.refused"]
    assert store.read(OWNER_SECRET_TARGET) is None
    assert pair_host(running.base_url, PRACTICE_OWNER_ID, secret, code, store) == []


def test_a_vault_refusal_after_pairing_is_reported_not_raised(
    host: tuple[PracticeHost, str],
) -> None:
    class BrokenWrite(MemoryCredentialStore):
        def write(self, target: str, secret: str) -> None:
            raise CredentialError("Credential Manager could not write it (Windows error 5).")

    running, secret = host
    problems = pair_host(
        running.base_url, PRACTICE_OWNER_ID, secret, running.issue_code(), BrokenWrite()
    )
    assert [problem.code for problem in problems] == ["owner.vault"]
    assert "Get a new pairing code" in problems[0].message


def test_bad_input_stops_before_any_host_address_is_checked() -> None:
    problems = pair_host(
        "https://host.example:8443", "owner-1", "x" * 32, "bad", MemoryCredentialStore()
    )
    assert [problem.code for problem in problems] == ["pair.code_format"]


def test_pairing_with_a_real_host_address_is_refused_until_its_pin_exists() -> None:
    problems = pair_host(
        "https://host.example:8443", "owner-1", "x" * 32, "ABCD-EFGH", MemoryCredentialStore()
    )
    assert [problem.code for problem in problems] == ["host.not_loopback"]


def test_pairing_with_an_unreachable_host_saves_nothing() -> None:
    store = MemoryCredentialStore()
    problems = pair_host(_closed_loopback_url(), PRACTICE_OWNER_ID, "x" * 32, "ABCD-EFGH", store)
    assert [problem.code for problem in problems] == ["host.unreachable"]
    assert store.read(OWNER_SECRET_TARGET) is None
