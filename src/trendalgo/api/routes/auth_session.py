"""Owner session bearer mint/revoke (AUTH-05)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/auth/session")
def mint_session(request: Request) -> dict[str, Any]:
    """Issue a short-lived bearer. Caller must already pass require_owner (HMAC)."""
    state = request.app.state.trendalgo
    issued = state.bearer_store.mint()
    return {
        "token_type": "bearer",
        "access_token": issued.token,
        "expires_at": issued.expires_at,
    }


@router.post("/auth/revoke")
async def revoke_session(request: Request) -> dict[str, str]:
    """Revoke the bearer presented in Authorization (or JSON body token)."""
    state = request.app.state.trendalgo
    auth = request.headers.get("Authorization", "")
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    if not token:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            token = str(body.get("token", "")).strip()
    if token:
        state.bearer_store.revoke(token)
    return {"status": "revoked"}
