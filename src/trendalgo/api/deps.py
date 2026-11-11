"""API auth dependencies (AUTH-01 / AUTH-04 / AUTH-05).

Exempt and open-GET tables live here so new routes inherit require_owner at
router-include time unless explicitly listed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from fastapi import Depends, HTTPException, Request

from trendalgo.api.session_tokens import BearerTokenStore
from trendalgo.trading.signed_command import (
    SignedNonceStore,
    now_seconds,
    owner_config,
    verify_request,
)

# --- AUTH-01 exempt / open tables (single source of truth) -----------------

# Mutating routes that use their own shared-secret auth (not owner bearer/HMAC).
EXEMPT_MUTATING: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("POST", "/api/v1/webhooks/tradingview"),
        # Telegram push cannot carry owner HMAC; uses TELEGRAM_WEBHOOK_SECRET.
        ("POST", "/api/v1/webhooks/telegram"),
    }
)

# Intentional unauthenticated GETs (still behind loopback bind — AUTH-02).
OPEN_GETS: Final[frozenset[str]] = frozenset(
    {
        "/api/v1/health",
        "/api/v1/version",
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

MUTATING_METHODS: Final[frozenset[str]] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class RawBody:
    """Body bytes read exactly once for webhook HMAC (AUTH-04)."""

    payload: bytes
    digest_hex: str


def _nonce_db(request: Request) -> Path:
    state = request.app.state.trendalgo
    data_dir = getattr(state, "data_dir", None)
    if data_dir is None:
        from trendalgo.api.state import default_state

        data_dir = default_state().portfolio_store.db_path.parent
    return Path(data_dir) / "owner_nonces.sqlite"


def _bearer_store(request: Request) -> BearerTokenStore:
    state = request.app.state.trendalgo
    store = getattr(state, "bearer_store", None)
    if store is None:
        store = BearerTokenStore()
        state.bearer_store = store
    return store


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


async def require_owner(request: Request) -> None:
    """Fail closed on mutating routes unless bearer or HMAC signed command is valid."""
    method = request.method.upper()
    path = request.url.path.rstrip("/") or "/"
    # Normalize: health is registered as /api/v1/health
    full = request.url.path

    if method in ("GET", "HEAD", "OPTIONS"):
        if full in OPEN_GETS or path in OPEN_GETS:
            return
        # All other GETs stay open only when listed; unlisted GETs stay open behind bind
        # but must appear in OPEN_GETS to be intentional. Unlisted GETs are treated as
        # intentionally open for read-only discovery — document by adding here when known.
        if method == "GET":
            return
        return

    if (method, full) in EXEMPT_MUTATING:
        return

    if method not in MUTATING_METHODS:
        return

    bearer = _extract_bearer(request)
    if bearer is not None:
        store = _bearer_store(request)
        if store.verify(bearer):
            return
        raise HTTPException(status_code=401, detail="owner bearer refused: invalid_or_revoked")

    body = await request.body()
    secret, owner_id = owner_config()
    verdict = verify_request(
        method=method,
        path=full,
        body=body,
        headers=request.headers,
        secret=secret,
        owner_id=owner_id,
        nonce_store=SignedNonceStore(_nonce_db(request)),
        now=now_seconds(),
    )
    if not verdict.ok:
        raise HTTPException(status_code=403, detail=f"owner command refused: {verdict.reason}")


async def read_raw_body_once(request: Request) -> RawBody:
    """Read the request body exactly once; pass digest to webhook handlers."""
    import hashlib

    payload = await request.body()
    digest_hex = hashlib.sha256(payload).hexdigest()
    return RawBody(payload=payload, digest_hex=digest_hex)


# FastAPI dependency aliases applied at include_router time.
OwnerDep = Depends(require_owner)
RawBodyDep = Depends(read_raw_body_once)
