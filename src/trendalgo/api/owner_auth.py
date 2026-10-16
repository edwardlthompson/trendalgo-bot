"""FastAPI guard for owner-signed host commands (H3). Fails closed."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request

from trendalgo.trading.signed_command import (
    SignedNonceStore,
    now_seconds,
    owner_config,
    verify_request,
)


async def require_owner_command(request: Request, nonce_db: Path) -> None:
    """Raise 403 unless the request carries a valid owner signature for this exact path and body."""
    body = await request.body()
    secret, owner_id = owner_config()
    verdict = verify_request(
        method=request.method,
        path=request.url.path,
        body=body,
        headers=request.headers,
        secret=secret,
        owner_id=owner_id,
        nonce_store=SignedNonceStore(nonce_db),
        now=now_seconds(),
    )
    if not verdict.ok:
        raise HTTPException(status_code=403, detail=f"owner command refused: {verdict.reason}")
