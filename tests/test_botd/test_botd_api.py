"""ADR-0016 host API: every route is owner-signed; plan sync, pairing, status and events."""

from __future__ import annotations

import json
from collections.abc import Callable
from itertools import count
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trendalgo.botd.api import create_botd_app
from trendalgo.botd.bundle import bundle_hash
from trendalgo.botd.guard import FixedWindowLimiter
from trendalgo.botd.heartbeat import Heartbeat
from trendalgo.botd.host_store import HostStore
from trendalgo.botd.outbox import Outbox
from trendalgo.botd.pairing import PAIRING_TTL_S, PairingCodes
from trendalgo.trading.signed_command import HEADER_SIGNATURE, MAX_SKEW_S, sign_request

NOW = 1_800_000_000
OWNER = "owner-1"
SECRET = "owner-secret-for-tests-only"
STATUS = "/api/v1/status"
PLAN = "/api/v1/plan"
_NONCES = count(1)


def _signed(
    method: str,
    path: str,
    body: bytes = b"",
    *,
    owner: str = OWNER,
    secret: str = SECRET,
    ts: int = NOW,
) -> dict[str, str]:
    """Headers as the owner's device signs them. Each call gets a fresh nonce."""
    return sign_request(
        method=method,
        path=path,
        body=body,
        owner_id=owner,
        secret=secret,
        timestamp=ts,
        nonce=f"nonce-{next(_NONCES):016d}",
    )


def _app(
    tmp_path: Path,
    store: HostStore,
    *,
    secret_provider: Callable[[], str | None] = lambda: SECRET,
    limiter: FixedWindowLimiter | None = None,
) -> FastAPI:
    return create_botd_app(
        store=store,
        host_owner_id=OWNER,
        nonce_db=tmp_path / "nonces.db",
        secret_provider=secret_provider,
        clock=lambda: NOW,
        limiter=limiter or FixedWindowLimiter(limit=1000),
    )


def _bundle(
    plan_version: int = 1,
    *,
    owner: str = OWNER,
    payload: dict[str, Any] | None = None,
    claimed_hash: str | None = None,
) -> bytes:
    body = payload if payload is not None else {"bots": [{"id": "bot-1", "pair": "BTC/USD"}]}
    header = {
        "owner_id": owner,
        "publisher": "owner",
        "kid": "owner-key-1",
        "plan_version": plan_version,
        "bundle_hash": claimed_hash or bundle_hash(body),
    }
    return json.dumps({"header": header, "payload": body}, sort_keys=True).encode()


def _put(client: TestClient, raw: bytes, *, ts: int = NOW) -> Any:
    return client.put(PLAN, content=raw, headers=_signed("PUT", PLAN, raw, ts=ts))


@pytest.fixture
def store(tmp_path: Path) -> HostStore:
    return HostStore(tmp_path / "host.db")


@pytest.fixture
def client(tmp_path: Path, store: HostStore) -> TestClient:
    return TestClient(_app(tmp_path, store))


def test_every_route_refuses_an_unsigned_request(client: TestClient) -> None:
    assert client.get(STATUS).status_code == 403
    assert client.get("/api/v1/events").status_code == 403
    assert client.put(PLAN, content=_bundle()).status_code == 403
    assert client.post("/api/v1/events/ack", content=b'{"ids":[]}').status_code == 403
    assert client.post("/api/v1/pair", content=b'{"code":"X"}').status_code == 403
    assert client.post("/api/v1/commands", content=b'{"action":"pause"}').status_code == 403
    assert (
        client.put("/api/v1/telegram", content=b'{"bot_token":"t","chat_id":"1"}').status_code
        == 403
    )


def test_a_signed_status_reports_an_empty_host(client: TestClient) -> None:
    response = client.get(STATUS, headers=_signed("GET", STATUS))
    assert response.status_code == 200
    assert response.json() == {
        "plan_version": 0,
        "bundle_hash": "",
        "positions": 0,
        "pending_events": 0,
        "last_beat": None,
    }


def test_a_signed_status_shows_the_last_heartbeat(tmp_path: Path, store: HostStore) -> None:
    Heartbeat(store).beat(NOW - 30)
    client = TestClient(_app(tmp_path, store))
    body = client.get(STATUS, headers=_signed("GET", STATUS)).json()
    assert body["last_beat"] == NOW - 30


def test_a_signed_plan_is_stored_and_reported(client: TestClient) -> None:
    raw = _bundle(1)
    payload = json.loads(raw)["payload"]
    response = _put(client, raw)
    assert response.status_code == 200
    assert response.json() == {"plan_version": 1, "bundle_hash": bundle_hash(payload)}
    status = client.get(STATUS, headers=_signed("GET", STATUS)).json()
    assert status["plan_version"] == 1
    assert status["bundle_hash"] == bundle_hash(payload)


def test_an_equal_or_older_plan_version_is_a_conflict(client: TestClient) -> None:
    newer = _bundle(2)
    assert _put(client, newer).status_code == 200
    assert _put(client, newer).status_code == 409
    assert _put(client, _bundle(1)).status_code == 409


def test_a_bundle_hash_that_does_not_match_its_payload_is_unprocessable(
    client: TestClient,
) -> None:
    assert _put(client, _bundle(1, claimed_hash="0" * 64)).status_code == 422


def test_a_plan_version_must_be_a_positive_integer(client: TestClient) -> None:
    assert _put(client, _bundle(0)).status_code == 422


def test_a_bundle_for_another_owner_is_refused(client: TestClient) -> None:
    response = _put(client, _bundle(1, owner="owner-2"))
    assert response.status_code == 403
    assert "foreign_owner" in response.json()["detail"]


def test_a_plan_must_be_a_json_object_with_header_and_payload(client: TestClient) -> None:
    for raw in (b"[1,2]", b'{"header": {}}', b"{not json"):
        assert _put(client, raw).status_code == 400


def test_a_forged_signature_is_refused(client: TestClient) -> None:
    headers = _signed("GET", STATUS)
    headers[HEADER_SIGNATURE] = "0" * 64
    response = client.get(STATUS, headers=headers)
    assert response.status_code == 403
    assert "bad_signature" in response.json()["detail"]


def test_a_replayed_request_is_refused(client: TestClient) -> None:
    headers = _signed("GET", STATUS)
    assert client.get(STATUS, headers=headers).status_code == 200
    response = client.get(STATUS, headers=headers)
    assert response.status_code == 403
    assert "replayed" in response.json()["detail"]


def test_a_stale_request_is_refused_and_the_skew_limit_is_inclusive(client: TestClient) -> None:
    stale = client.get(STATUS, headers=_signed("GET", STATUS, ts=NOW - MAX_SKEW_S - 1))
    assert stale.status_code == 403
    assert "stale" in stale.json()["detail"]
    edge = client.get(STATUS, headers=_signed("GET", STATUS, ts=NOW - MAX_SKEW_S))
    assert edge.status_code == 200


def test_a_foreign_owner_header_is_refused(client: TestClient) -> None:
    response = client.get(STATUS, headers=_signed("GET", STATUS, owner="owner-2"))
    assert response.status_code == 403
    assert "foreign_owner" in response.json()["detail"]


def test_a_host_without_its_owner_secret_fails_closed(tmp_path: Path, store: HostStore) -> None:
    client = TestClient(_app(tmp_path, store, secret_provider=lambda: None))
    response = client.get(STATUS, headers=_signed("GET", STATUS))
    assert response.status_code == 403
    assert "owner_secret_missing" in response.json()["detail"]


def test_a_flood_is_rate_limited_before_the_signature_is_checked(
    tmp_path: Path, store: HostStore
) -> None:
    client = TestClient(_app(tmp_path, store, limiter=FixedWindowLimiter(limit=2)))
    for _ in range(2):
        assert client.get(STATUS, headers=_signed("GET", STATUS)).status_code == 200
    assert client.get(STATUS).status_code == 429


def test_queued_events_are_listed_and_acknowledged(client: TestClient, store: HostStore) -> None:
    Outbox(store, host_owner_id=OWNER).enqueue(
        owner_id=OWNER, dedupe_key="fill-1", kind="fill", payload={"qty": 0.5}, now=NOW
    )
    listed = client.get("/api/v1/events", headers=_signed("GET", "/api/v1/events")).json()
    events = listed["events"]
    assert [(event["kind"], event["payload"]) for event in events] == [("fill", {"qty": 0.5})]
    body = json.dumps({"ids": [events[0]["id"]]}).encode()
    acked = client.post(
        "/api/v1/events/ack",
        content=body,
        headers=_signed("POST", "/api/v1/events/ack", body),
    )
    assert acked.json() == {"removed": 1}
    remaining = client.get("/api/v1/events", headers=_signed("GET", "/api/v1/events")).json()
    assert remaining["events"] == []


def test_an_ack_must_list_integer_ids(client: TestClient) -> None:
    for ids in (["1"], [True], "1"):
        body = json.dumps({"ids": ids}).encode()
        response = client.post(
            "/api/v1/events/ack",
            content=body,
            headers=_signed("POST", "/api/v1/events/ack", body),
        )
        assert response.status_code == 400


def test_a_pairing_code_redeems_once_over_a_signed_request(
    client: TestClient, store: HostStore
) -> None:
    code = PairingCodes(store).issue(NOW)
    body = json.dumps({"code": code}).encode()
    first = client.post("/api/v1/pair", content=body, headers=_signed("POST", "/api/v1/pair", body))
    assert first.json() == {"paired": True}
    second = client.post(
        "/api/v1/pair", content=body, headers=_signed("POST", "/api/v1/pair", body)
    )
    assert second.status_code == 403
    assert "pairing code refused" in second.json()["detail"]


def test_an_expired_or_wrong_pairing_code_is_refused(client: TestClient, store: HostStore) -> None:
    expired = PairingCodes(store).issue(NOW - PAIRING_TTL_S - 1)
    for code in (expired, "AAAA-AAAA", None):
        body = json.dumps({"code": code}).encode()
        response = client.post(
            "/api/v1/pair", content=body, headers=_signed("POST", "/api/v1/pair", body)
        )
        assert response.status_code == 403


def test_a_signed_command_is_accepted_and_deduped(client: TestClient) -> None:
    path = "/api/v1/commands"
    body = json.dumps({"action": "pause", "bot_id": "bot-1", "idempotency_key": "idem-1"}).encode()
    first = client.post(path, content=body, headers=_signed("POST", path, body))
    assert first.status_code == 200
    assert first.json()["accepted"] is True
    assert first.json()["duplicate"] is False
    second = client.post(path, content=body, headers=_signed("POST", path, body))
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    events = client.get("/api/v1/events", headers=_signed("GET", "/api/v1/events")).json()
    assert len(events["events"]) == 1
    assert events["events"][0]["kind"] == "command"


def test_a_command_without_fields_is_unprocessable(client: TestClient) -> None:
    path = "/api/v1/commands"
    body = b'{"action":"nope"}'
    response = client.post(path, content=body, headers=_signed("POST", path, body))
    assert response.status_code == 422


def test_signed_telegram_sync_stores_secrets(tmp_path: Path, store: HostStore) -> None:
    from trendalgo.botd.telegram_secrets import load_creds, load_trade_alerts

    app = create_botd_app(
        store=store,
        host_owner_id=OWNER,
        nonce_db=tmp_path / "nonces.db",
        secret_provider=lambda: SECRET,
        clock=lambda: NOW,
        limiter=FixedWindowLimiter(limit=1000),
        secrets_root=tmp_path,
    )
    client = TestClient(app)
    path = "/api/v1/telegram"
    body = json.dumps(
        {
            "bot_token": "tok-abc",
            "chat_id": "42",
            "trade_alerts": True,
            "telegram_enabled": True,
            "telegram_trades": True,
        }
    ).encode()
    response = client.put(path, content=body, headers=_signed("PUT", path, body))
    assert response.status_code == 200
    assert response.json() == {"saved": True}
    assert load_creds(tmp_path) == ("tok-abc", "42")
    assert load_trade_alerts(tmp_path) is True
