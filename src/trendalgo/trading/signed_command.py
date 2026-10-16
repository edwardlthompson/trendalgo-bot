"""Owner-signed host commands (H3).

Each command carries an HMAC-SHA256 over method, path, timestamp, nonce, owner_id, and a
SHA-256 digest of the body. The host rejects clock skew over 300 seconds, a replayed nonce
(nonces are kept for 24 hours), a foreign owner, and a bad signature. The device pins the
host certificate fingerprint with `host_certificate_pinned`.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from trendalgo.exchanges.secrets import EnvSecretStore

MAX_SKEW_S = 300
NONCE_TTL_S = 24 * 60 * 60
HEADER_TIMESTAMP = "X-Trendalgo-Timestamp"
HEADER_NONCE = "X-Trendalgo-Nonce"
HEADER_OWNER = "X-Trendalgo-Owner"
HEADER_SIGNATURE = "X-Trendalgo-Signature"
OWNER_SECRET_ENV = "TRENDALGO_OWNER_SECRET"
OWNER_ID_ENV = "TRENDALGO_OWNER_ID"
_NONCE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,64}")


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str


def canonical_string(
    *, method: str, path: str, timestamp: int, nonce: str, owner_id: str, body: bytes
) -> bytes:
    body_digest = hashlib.sha256(body).hexdigest()
    parts = [method.upper(), path, str(timestamp), nonce, owner_id, body_digest]
    return "\n".join(parts).encode()


def _hmac_hex(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def sign_request(
    *,
    method: str,
    path: str,
    body: bytes,
    owner_id: str,
    secret: str,
    timestamp: int,
    nonce: str,
) -> dict[str, str]:
    """Headers for one owner-signed command. Used by the go-live CLI and by tests."""
    message = canonical_string(
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        owner_id=owner_id,
        body=body,
    )
    return {
        HEADER_TIMESTAMP: str(timestamp),
        HEADER_NONCE: nonce,
        HEADER_OWNER: owner_id,
        HEADER_SIGNATURE: _hmac_hex(secret, message),
    }


class SignedNonceStore:
    """Single-use nonces, kept for 24 hours. Replays are refused across restarts."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def remember(self, nonce: str, now: int) -> bool:
        """Record a nonce. False if it was already seen within the TTL (a replay)."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS owner_nonces "
                "(nonce TEXT PRIMARY KEY, seen_at INTEGER NOT NULL)"
            )
            conn.execute("DELETE FROM owner_nonces WHERE seen_at < ?", (now - NONCE_TTL_S,))
            try:
                conn.execute(
                    "INSERT INTO owner_nonces (nonce, seen_at) VALUES (?, ?)", (nonce, now)
                )
            except sqlite3.IntegrityError:
                return False
            return True


def verify_request(
    *,
    method: str,
    path: str,
    body: bytes,
    headers: Mapping[str, str],
    secret: str | None,
    owner_id: str | None,
    nonce_store: SignedNonceStore,
    now: int,
) -> Verdict:
    """Fail-closed check. The nonce is recorded only after the signature is valid."""
    if not secret:
        return Verdict(ok=False, reason="owner_secret_missing")
    if not owner_id:
        return Verdict(ok=False, reason="owner_id_missing")
    timestamp_raw = headers.get(HEADER_TIMESTAMP)
    nonce = headers.get(HEADER_NONCE)
    owner = headers.get(HEADER_OWNER)
    signature = headers.get(HEADER_SIGNATURE)
    if not (timestamp_raw and nonce and owner and signature):
        return Verdict(ok=False, reason="missing_headers")
    if not hmac.compare_digest(owner.encode(), owner_id.encode()):
        return Verdict(ok=False, reason="foreign_owner")
    try:
        timestamp = int(timestamp_raw)
    except ValueError:
        return Verdict(ok=False, reason="bad_timestamp")
    if abs(now - timestamp) > MAX_SKEW_S:
        return Verdict(ok=False, reason="stale")
    if _NONCE_PATTERN.fullmatch(nonce) is None:
        return Verdict(ok=False, reason="bad_nonce")
    message = canonical_string(
        method=method,
        path=path,
        timestamp=timestamp,
        nonce=nonce,
        owner_id=owner_id,
        body=body,
    )
    if not hmac.compare_digest(signature.lower(), _hmac_hex(secret, message)):
        return Verdict(ok=False, reason="bad_signature")
    if not nonce_store.remember(nonce, now):
        return Verdict(ok=False, reason="replayed")
    return Verdict(ok=True, reason="ok")


def owner_config() -> tuple[str | None, str | None]:
    """The owner secret comes from the secret port; the owner id is not secret."""
    secret = EnvSecretStore().get(OWNER_SECRET_ENV)
    owner_id = os.environ.get(OWNER_ID_ENV) or None
    return secret, owner_id


def host_certificate_pinned(expected_sha256: str | None, presented_sha256: str) -> bool:
    """The device talks to the host only when the certificate SHA-256 matches the pin."""
    if not expected_sha256 or not presented_sha256:
        return False
    return hmac.compare_digest(
        _normalize_fingerprint(expected_sha256), _normalize_fingerprint(presented_sha256)
    )


def _normalize_fingerprint(value: str) -> str:
    return value.replace(":", "").strip().lower()


def now_seconds() -> int:
    return int(time.time())
