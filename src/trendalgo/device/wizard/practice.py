"""Practice mode (row 19): the real host API on 127.0.0.1, with its own database and a practice secret.

Four checks run against it: a signed status call; a call signed with the wrong secret (must be
refused); a pairing code that works once; and the same code again (must be refused). Nothing here
reaches an exchange. The practice secret lives in Credential Manager, never in a file.
"""

from __future__ import annotations

import socket
import sqlite3
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import TracebackType
from typing import Any

from trendalgo.botd.api import create_botd_app
from trendalgo.botd.host_store import HostStore
from trendalgo.botd.pairing import PairingCodes
from trendalgo.device.host_client import PAIR_PATH, STATUS_PATH
from trendalgo.device.wizard.credentials import (
    PRACTICE_SECRET_TARGET,
    CredentialError,
    CredentialStore,
    get_or_create_secret,
)
from trendalgo.device.wizard.hostclient import HostClient
from trendalgo.device.wizard.validators import LOOPBACK_HOST, Problem
from trendalgo.trading.signed_command import now_seconds

PRACTICE_OWNER_ID = "practice"
START_TIMEOUT_S = 10.0
_POLL_S = 0.02


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((LOOPBACK_HOST, 0))
        return int(sock.getsockname()[1])


class PracticeHost:
    """The host API on 127.0.0.1 until the block exits. It runs in a thread of this process."""

    def __init__(self, root: Path, secret: str) -> None:
        self._root = root
        self._secret = secret
        self._server: Any = None
        self._thread: threading.Thread | None = None
        self._store: HostStore | None = None
        self.base_url = ""

    def __enter__(self) -> PracticeHost:
        import uvicorn  # loaded only when practice mode runs

        folder = self._root / "practice"
        self._store = HostStore(folder / "host.db")
        app = create_botd_app(
            store=self._store,
            host_owner_id=PRACTICE_OWNER_ID,
            nonce_db=folder / "nonces.db",
            secret_provider=lambda: self._secret,
        )
        port = _free_port()
        config = uvicorn.Config(
            app,
            host=LOOPBACK_HOST,
            port=port,
            log_level="warning",
            lifespan="off",
            ws="none",  # the host has no websocket route; keep that stack out of the process
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + START_TIMEOUT_S
        while not self._server.started:
            if time.monotonic() > deadline or not self._thread.is_alive():
                self._stop()
                raise RuntimeError("the host did not start on 127.0.0.1")
            time.sleep(_POLL_S)
        self.base_url = f"http://{LOOPBACK_HOST}:{port}"
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stop()

    def _stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=START_TIMEOUT_S)

    def issue_code(self) -> str:
        if self._store is None:
            raise RuntimeError("the host is not running")
        return PairingCodes(self._store).issue(now_seconds())


def run_practice(
    root: Path,
    store: CredentialStore,
    *,
    clock: Callable[[], int] = now_seconds,
) -> list[Problem]:
    """Run the four practice checks on a fresh loopback host. An empty list means all passed."""
    try:
        secret = get_or_create_secret(store, PRACTICE_SECRET_TARGET)
        with PracticeHost(root, secret) as host:
            # The address is built from 127.0.0.1 here, so HostClient cannot refuse it.
            client = HostClient(host.base_url, PRACTICE_OWNER_ID, secret, clock=clock)
            return _run_checks(client, host, secret)
    except CredentialError as exc:
        return [Problem("practice.vault", str(exc))]
    except (RuntimeError, OSError, sqlite3.Error) as exc:
        return [Problem("practice.host_failed", f"Practice mode could not start: {exc}")]


def _run_checks(client: HostClient, host: PracticeHost, secret: str) -> list[Problem]:
    problems: list[Problem] = []
    if client.call("GET", STATUS_PATH) != 200:
        problems.append(
            Problem("practice.status_refused", "The host refused a signed status call.")
        )
    if client.call("GET", STATUS_PATH, secret="wrong-" + secret) != 403:
        problems.append(
            Problem(
                "practice.forgery_accepted",
                "The host accepted a call signed with the wrong secret. Stop and report this.",
            )
        )
    code = host.issue_code()
    if client.call("POST", PAIR_PATH, {"code": code}) != 200:
        problems.append(Problem("practice.pair_refused", "The host refused a fresh pairing code."))
        return problems
    if client.call("POST", PAIR_PATH, {"code": code}) != 403:
        problems.append(
            Problem(
                "practice.reuse_accepted",
                "The host accepted a pairing code twice. Stop and report this.",
            )
        )
    return problems
