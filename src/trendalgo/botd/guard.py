"""Request guard for the host API: a fixed-window rate limit (W-PORT), then the owner HMAC (H3)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException, Request

from trendalgo.trading.signed_command import SignedNonceStore, now_seconds, verify_request

DEFAULT_LIMIT = 60
WINDOW_S = 60


class FixedWindowLimiter:
    """At most `limit` requests per key in each window. Counts are in memory and reset on restart."""

    def __init__(self, *, limit: int = DEFAULT_LIMIT, window_s: int = WINDOW_S) -> None:
        if limit < 1 or window_s < 1:
            raise ValueError("limit and window_s must be positive")
        self.limit = limit
        self.window_s = window_s
        self._counts: dict[tuple[str, int], int] = {}

    def allow(self, key: str, now: int) -> bool:
        window = now // self.window_s
        count = self._counts.get((key, window), 0)
        if count >= self.limit:
            return False
        self._counts[(key, window)] = count + 1
        for stale in [bucket for bucket in self._counts if bucket[1] < window]:
            del self._counts[stale]
        return True


class OwnerGuard:
    def __init__(
        self,
        *,
        owner_id: str,
        nonce_db: Path,
        secret_provider: Callable[[], str | None],
        limiter: FixedWindowLimiter,
        clock: Callable[[], int] = now_seconds,
    ) -> None:
        self.owner_id = owner_id
        self.nonce_store = SignedNonceStore(nonce_db)
        self.secret_provider = secret_provider
        self.limiter = limiter
        self.clock = clock

    async def require(self, request: Request) -> None:
        """429 when over the rate limit; 403 unless the owner signed this exact request."""
        now = self.clock()
        if not self.limiter.allow(request.url.path, now):
            raise HTTPException(status_code=429, detail="rate limited")
        verdict = verify_request(
            method=request.method,
            path=request.url.path,
            body=await request.body(),
            headers=request.headers,
            secret=self.secret_provider(),
            owner_id=self.owner_id,
            nonce_store=self.nonce_store,
            now=now,
        )
        if not verdict.ok:
            raise HTTPException(status_code=403, detail=f"owner command refused: {verdict.reason}")
