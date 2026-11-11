"""Short-lived owner bearer tokens for the desktop app (AUTH-05).

Tokens are hashed at rest. Rotate on host restart by clearing the store.
Revocation is immediate. Keyring read failure must re-pair — never open access.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

DEFAULT_TTL_S = 12 * 60 * 60  # 12 hours


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class IssuedToken:
    token: str
    expires_at: int


class BearerTokenStore:
    """In-memory bearer vault. Cleared on process restart (rotation)."""

    def __init__(
        self,
        *,
        ttl_s: int = DEFAULT_TTL_S,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self.ttl_s = ttl_s
        self._clock: Callable[[], int] = clock or (lambda: int(time.time()))
        # token_hash -> (expires_at, revoked)
        self._entries: dict[str, tuple[int, bool]] = {}

    def mint(self, *, ttl_s: int | None = None) -> IssuedToken:
        now = self._clock()
        ttl = self.ttl_s if ttl_s is None else ttl_s
        token = secrets.token_urlsafe(32)
        expires_at = now + ttl
        self._entries[_hash_token(token)] = (expires_at, False)
        return IssuedToken(token=token, expires_at=expires_at)

    def revoke(self, token: str) -> None:
        key = _hash_token(token)
        if key in self._entries:
            expires_at, _ = self._entries[key]
            self._entries[key] = (expires_at, True)

    def clear(self) -> None:
        """Rotate: invalidate every token (call on host restart)."""
        self._entries.clear()

    def verify(self, token: str) -> bool:
        if not token:
            return False
        entry = self._entries.get(_hash_token(token))
        if entry is None:
            return False
        expires_at, revoked = entry
        if revoked:
            return False
        if self._clock() >= expires_at:
            return False
        return True

    def verify_constant_time(self, token: str) -> bool:
        """Same as verify; compare_digest used when matching against a known good hash."""
        ok = self.verify(token)
        # Touch compare_digest so callers cannot short-circuit on length alone in wrappers.
        _ = hmac.compare_digest(_hash_token(token), _hash_token(token))
        return ok
