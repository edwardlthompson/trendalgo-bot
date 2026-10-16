"""Owner-signed HTTP client for the host API (ADR-0016). Shared by the wizard and device UI."""

from __future__ import annotations

import hashlib
import http.client
import json
import secrets
import socket
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from trendalgo.device.wizard.validators import LOOPBACK_HOST, Problem, check_loopback_url
from trendalgo.trading.signed_command import host_certificate_pinned, now_seconds, sign_request

STATUS_PATH = "/api/v1/status"
PLAN_PATH = "/api/v1/plan"
EVENTS_PATH = "/api/v1/events"
EVENTS_ACK_PATH = "/api/v1/events/ack"
COMMANDS_PATH = "/api/v1/commands"
PAIR_PATH = "/api/v1/pair"
TELEGRAM_PATH = "/api/v1/telegram"
PORTFOLIO_PATH = "/api/v1/portfolio"
CALL_TIMEOUT_S = 10.0
UNREACHABLE = 0


@dataclass(frozen=True)
class HostResponse:
    status: int
    data: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status == 200


class HostRefusedError(RuntimeError):
    def __init__(self, problem: Problem) -> None:
        super().__init__(problem.message)
        self.problem = problem


def check_host_address(
    url: str,
    *,
    cert_sha256: str | None,
    loopback_only: bool = False,
) -> Problem | None:
    """Loopback http is always allowed. Other hosts need https and a cert pin in settings."""
    if loopback_only:
        return check_loopback_url(url)
    if _is_loopback_http(url):
        return None
    parts = _url_parts(url)
    if parts is None:
        return Problem(
            "host.not_allowed", "Use http://127.0.0.1:<port> or https:// with a pinned certificate."
        )
    if parts.scheme != "https":
        return Problem(
            "host.not_allowed", "A remote host must use https:// with a pinned certificate."
        )
    if not (cert_sha256 or "").strip():
        return Problem(
            "host.pin_missing",
            "Add the host certificate SHA-256 pin in settings before calling a remote host.",
        )
    return None


class HostClient:
    def __init__(
        self,
        base_url: str,
        owner_id: str,
        secret: str,
        *,
        cert_sha256: str | None = None,
        loopback_only: bool = False,
        tls_fingerprint: Callable[[str, int], str] | None = None,
        clock: Callable[[], int] = now_seconds,
    ) -> None:
        problem = check_host_address(base_url, cert_sha256=cert_sha256, loopback_only=loopback_only)
        if problem is not None:
            raise HostRefusedError(problem)
        self._base = base_url.rstrip("/")
        self._owner = owner_id
        self._secret = secret
        self._pin = (cert_sha256 or "").strip() or None
        self._loopback_only = loopback_only
        self._tls_fingerprint = tls_fingerprint or _tls_sha256
        self._clock = clock
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        secret: str | None = None,
    ) -> int:
        return self.request(method, path, payload, secret=secret).status

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        secret: str | None = None,
    ) -> HostResponse:
        if not self._pin_ok():
            raise HostRefusedError(
                Problem(
                    "host.pin_mismatch",
                    "The host certificate does not match the pin saved on this PC.",
                )
            )
        body = b"" if payload is None else json.dumps(payload, sort_keys=True).encode("utf-8")
        headers = sign_request(
            method=method,
            path=path,
            body=body,
            owner_id=self._owner,
            secret=self._secret if secret is None else secret,
            timestamp=self._clock(),
            nonce=secrets.token_urlsafe(16),
        )
        if body:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._base + path, data=body or None, headers=headers, method=method
        )
        try:
            with self._opener.open(request, timeout=CALL_TIMEOUT_S) as response:
                raw = response.read()
                return HostResponse(int(response.status), _json_dict(raw))
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return HostResponse(int(exc.code), _json_dict(raw))
        except (OSError, http.client.HTTPException):
            return HostResponse(UNREACHABLE, None)

    def get_status(self) -> HostResponse:
        return self.request("GET", STATUS_PATH)

    def get_portfolio(self) -> HostResponse:
        return self.request("GET", PORTFOLIO_PATH)

    def put_plan(self, bundle: dict[str, Any]) -> HostResponse:
        return self.request("PUT", PLAN_PATH, bundle)

    def get_events(self) -> HostResponse:
        return self.request("GET", EVENTS_PATH)

    def ack_events(self, ids: list[int]) -> HostResponse:
        return self.request("POST", EVENTS_ACK_PATH, {"ids": ids})

    def post_command(self, action: str, bot_id: str, idempotency_key: str) -> HostResponse:
        return self.request(
            "POST",
            COMMANDS_PATH,
            {"action": action, "bot_id": bot_id, "idempotency_key": idempotency_key},
        )

    def put_telegram(self, payload: dict[str, Any]) -> HostResponse:
        return self.request("PUT", TELEGRAM_PATH, payload)

    def _pin_ok(self) -> bool:
        if _is_loopback_http(self._base):
            return True
        parts = _url_parts(self._base)
        if parts is None or parts.hostname is None or parts.port is None:
            return False
        presented = self._tls_fingerprint(parts.hostname, parts.port)
        return host_certificate_pinned(self._pin, presented)


def _json_dict(raw: bytes) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _is_loopback_http(url: str) -> bool:
    parts = _url_parts(url)
    if parts is None:
        return False
    return parts.scheme == "http" and parts.hostname == LOOPBACK_HOST and parts.port is not None


def _url_parts(url: str) -> Any:
    try:
        return urlsplit(url)
    except ValueError:
        return None


def _tls_sha256(host: str, port: int) -> str:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=CALL_TIMEOUT_S) as sock:
        with context.wrap_socket(sock, server_hostname=host) as secured:
            der = secured.getpeercert(binary_form=True)
            if not der:
                return ""
            return hashlib.sha256(der).hexdigest()
