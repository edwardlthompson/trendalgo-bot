"""Shared host client: loopback practice, pinned https, and API helpers."""

from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from trendalgo.device.host_actions import portfolio_status_message, send_plan_bundle
from trendalgo.device.host_client import (
    STATUS_PATH,
    UNREACHABLE,
    HostClient,
    HostRefusedError,
    check_host_address,
)
from trendalgo.device.host_session import open_host_client
from trendalgo.device.plan_model import BotSpec, build_bundle, next_plan_version
from trendalgo.device.settings_model import Settings
from trendalgo.device.wizard.hostclient import HostClient as WizardHostClient
from trendalgo.device.wizard.practice import PRACTICE_OWNER_ID, PracticeHost


@pytest.fixture
def practice(tmp_path: Path) -> tuple[PracticeHost, str]:
    secret = secrets.token_urlsafe(32)
    with PracticeHost(tmp_path, secret) as running:
        yield running, secret


def test_wizard_client_still_refuses_remote_hosts() -> None:
    with pytest.raises(HostRefusedError) as info:
        WizardHostClient("https://host.example:8443", PRACTICE_OWNER_ID, "x" * 32)
    assert info.value.problem.code == "host.not_loopback"


def test_shared_client_allows_loopback_http(practice: tuple[PracticeHost, str]) -> None:
    host, secret = practice
    client = HostClient(host.base_url, PRACTICE_OWNER_ID, secret)
    response = client.get_status()
    assert response.ok
    assert int(response.data["plan_version"]) == 0


def test_remote_https_requires_a_pin() -> None:
    problem = check_host_address("https://host.example:8443", cert_sha256=None)
    assert problem is not None
    assert problem.code == "host.pin_missing"


def test_remote_https_accepts_matching_injected_pin(practice: tuple[PracticeHost, str]) -> None:
    host, secret = practice
    pin = "ab" * 32

    def always_pin(_host: str, _port: int) -> str:
        return pin

    client = HostClient(
        host.base_url.replace("http://", "https://"),
        PRACTICE_OWNER_ID,
        secret,
        cert_sha256=pin,
        tls_fingerprint=always_pin,
    )
    # Pin check passes, but nothing listens on https — unreachable is fine here.
    assert client.get_status().status == UNREACHABLE


def test_pin_mismatch_refuses_before_request() -> None:
    pin = "aa" * 32

    def wrong(_host: str, _port: int) -> str:
        return "bb" * 32

    with pytest.raises(HostRefusedError) as info:
        client = HostClient(
            "https://host.example:8443",
            "owner",
            "x" * 32,
            cert_sha256=pin,
            tls_fingerprint=wrong,
        )
        client.get_status()
    assert info.value.problem.code == "host.pin_mismatch"


def test_put_plan_and_events_on_practice_host(practice: tuple[PracticeHost, str]) -> None:
    host, secret = practice
    client = HostClient(host.base_url, PRACTICE_OWNER_ID, secret)
    bots = [
        BotSpec("A", "BTC/USD", "1h", "RSI", 100.0, 5.0),
    ]
    version = next_plan_version(0)
    bundle = build_bundle(bots, owner_id=PRACTICE_OWNER_ID, plan_version=version)
    ok, code = send_plan_bundle(client, bundle)
    assert ok and code.startswith("sent:")
    status = client.get_status()
    assert status.ok and int(status.data["plan_version"]) == version
    events = client.get_events()
    assert events.ok and isinstance(events.data.get("events"), list)


def test_open_from_settings_needs_secret(
    tmp_path: Path, practice: tuple[PracticeHost, str]
) -> None:
    host, _secret = practice
    settings = Settings(PRACTICE_OWNER_ID, host.base_url)
    assert open_host_client(settings, store=_EmptyVault()) is None


def test_portfolio_status_is_honest_when_missing(practice: tuple[PracticeHost, str]) -> None:
    host, secret = practice
    client = HostClient(host.base_url, PRACTICE_OWNER_ID, secret)
    ok, reason = portfolio_status_message(client.get_status())
    assert not ok and reason == "no_portfolio_payload"


class _EmptyVault:
    def read(self, target: str) -> str | None:
        return None

    def write(self, target: str, secret: str) -> None:
        pass

    def delete(self, target: str) -> None:
        pass


def test_signed_get_status_matches_wizard_call(practice: tuple[PracticeHost, str]) -> None:
    host, secret = practice
    shared = HostClient(host.base_url, PRACTICE_OWNER_ID, secret)
    wizard = WizardHostClient(host.base_url, PRACTICE_OWNER_ID, secret)
    assert shared.call("GET", STATUS_PATH) == wizard.call("GET", STATUS_PATH) == 200


def test_ack_events_round_trip(practice: tuple[PracticeHost, str]) -> None:
    host, secret = practice
    client = HostClient(host.base_url, PRACTICE_OWNER_ID, secret)
    client.post_command("pause", "bot-1", secrets.token_urlsafe(8))
    pending = client.get_events()
    ids = [int(item["id"]) for item in pending.data.get("events", []) if isinstance(item, dict)]
    if ids:
        ack = client.ack_events(ids)
        assert ack.ok
