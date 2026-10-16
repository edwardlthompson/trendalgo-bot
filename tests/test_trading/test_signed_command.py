"""H3: owner-signed commands reject forged, replayed, stale, foreign-owner, and wrong-cert requests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.trading.signed_command import (
    HEADER_NONCE,
    HEADER_OWNER,
    HEADER_TIMESTAMP,
    MAX_SKEW_S,
    NONCE_TTL_S,
    SignedNonceStore,
    host_certificate_pinned,
    sign_request,
    verify_request,
)

NOW = 1_800_000_000
SECRET = "owner-secret-for-tests-only"
OWNER = "owner-1"
PATH = "/api/v1/trading/exchanges/kraken/go-live"
NONCE = "nonce-0001-abcdefgh"


def _headers(
    *, path: str = PATH, owner: str = OWNER, secret: str = SECRET, ts: int = NOW, nonce: str = NONCE
) -> dict[str, str]:
    return sign_request(
        method="POST",
        path=path,
        body=b"",
        owner_id=owner,
        secret=secret,
        timestamp=ts,
        nonce=nonce,
    )


def _verify(
    store: SignedNonceStore,
    headers: dict[str, str],
    *,
    now: int = NOW,
    path: str = PATH,
    body: bytes = b"",
    secret: str | None = SECRET,
    owner_id: str | None = OWNER,
) -> str:
    verdict = verify_request(
        method="POST",
        path=path,
        body=body,
        headers=headers,
        secret=secret,
        owner_id=owner_id,
        nonce_store=store,
        now=now,
    )
    return verdict.reason if not verdict.ok else "ok"


def test_a_correctly_signed_request_is_accepted(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers()) == "ok"


def test_a_replayed_nonce_is_rejected(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers()) == "ok"
    assert _verify(store, _headers()) == "replayed"


def test_a_replay_is_still_refused_after_a_restart(tmp_path: Path) -> None:
    db = tmp_path / "nonces.db"
    assert _verify(SignedNonceStore(db), _headers()) == "ok"
    assert _verify(SignedNonceStore(db), _headers()) == "replayed"


def test_stale_and_future_timestamps_are_rejected_beyond_the_skew(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers(ts=NOW - MAX_SKEW_S - 1)) == "stale"
    assert _verify(store, _headers(ts=NOW + MAX_SKEW_S + 1)) == "stale"


def test_the_skew_boundary_itself_is_accepted(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers(ts=NOW - MAX_SKEW_S, nonce="nonce-skew-edge-0001")) == "ok"


def test_a_foreign_owner_is_rejected_even_with_a_valid_signature(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    foreign = _headers(owner="owner-2")
    assert _verify(store, foreign, owner_id=OWNER) == "foreign_owner"


def test_a_tampered_path_or_body_fails_the_signature(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers(), path="/api/v1/platform/dex/venues/base/go-live") == (
        "bad_signature"
    )
    assert _verify(store, _headers(), body=b"tampered") == "bad_signature"


def test_a_signature_from_another_secret_is_rejected(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers(secret="someone-else")) == "bad_signature"


def test_missing_owner_configuration_fails_closed(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, _headers(), secret=None) == "owner_secret_missing"
    assert _verify(store, _headers(), owner_id=None) == "owner_id_missing"
    assert _verify(store, _headers(), secret="") == "owner_secret_missing"


def test_missing_headers_and_malformed_fields_are_rejected(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert _verify(store, {}) == "missing_headers"
    assert _verify(store, {**_headers(), HEADER_TIMESTAMP: "not-a-number"}) == "bad_timestamp"
    assert _verify(store, {**_headers(), HEADER_NONCE: "short"}) == "bad_nonce"
    assert _verify(store, {**_headers(), HEADER_OWNER: ""}) == "missing_headers"


def test_a_bad_request_does_not_consume_its_nonce(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    forged = {**_headers(secret="someone-else"), HEADER_OWNER: OWNER}
    assert _verify(store, forged) == "bad_signature"
    assert _verify(store, _headers()) == "ok"


def test_the_nonce_store_forgets_after_24_hours(tmp_path: Path) -> None:
    store = SignedNonceStore(tmp_path / "nonces.db")
    assert store.remember("nonce-ttl-0000001", NOW) is True
    assert store.remember("nonce-ttl-0000001", NOW + NONCE_TTL_S - 1) is False
    assert store.remember("nonce-ttl-0000001", NOW + NONCE_TTL_S + 1) is True


def test_the_device_refuses_a_host_with_the_wrong_certificate() -> None:
    pinned = "AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89"
    same = pinned.replace(":", "").lower()
    assert host_certificate_pinned(pinned, same) is True
    assert host_certificate_pinned(pinned, "00" * 32) is False
    assert host_certificate_pinned(None, pinned) is False
    assert host_certificate_pinned(pinned, "") is False


def test_signed_headers_carry_the_owner_id_and_timestamp() -> None:
    headers = _headers()
    assert headers[HEADER_OWNER] == OWNER
    assert headers[HEADER_TIMESTAMP] == str(NOW)
