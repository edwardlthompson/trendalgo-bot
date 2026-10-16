"""Pairing codes (W-PAIR): single-use, 10-minute expiry. Only a hash of each code is stored."""

from __future__ import annotations

import hashlib
import secrets

from trendalgo.botd.host_store import HostStore

PAIRING_TTL_S = 10 * 60
CODE_ALPHABET = (
    "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0, O, 1 or I, so codes read aloud stay clear
)
CODE_LENGTH = 8


def _normalize(code: str) -> str:
    return code.replace("-", "").replace(" ", "").strip().upper()


def _hash(code: str) -> str:
    return hashlib.sha256(_normalize(code).encode()).hexdigest()


class PairingCodes:
    def __init__(self, store: HostStore) -> None:
        self.store = store

    def issue(self, now: int) -> str:
        """A new code, shown once on the host. Expired codes are pruned as a side effect."""
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        with self.store.connect() as conn:
            conn.execute("DELETE FROM pairing_codes WHERE expires_at < ?", (now,))
            conn.execute(
                "INSERT INTO pairing_codes (code_hash, expires_at, used) VALUES (?, ?, 0)",
                (_hash(code), now + PAIRING_TTL_S),
            )
        return f"{code[:4]}-{code[4:]}"

    def redeem(self, code: str, now: int) -> bool:
        """Consume a code. Refused when unknown, already used, or expired. Single-use is atomic."""
        with self.store.connect() as conn:
            cur = conn.execute(
                "UPDATE pairing_codes SET used = 1 "
                "WHERE code_hash = ? AND used = 0 AND expires_at >= ?",
                (_hash(code), now),
            )
            return cur.rowcount == 1
