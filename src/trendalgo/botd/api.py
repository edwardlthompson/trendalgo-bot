"""Host API (ADR-0016): owner-signed sync, pairing, status and events. Device-initiated only."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from trendalgo.botd.bundle import verify_bundle
from trendalgo.botd.commands import apply_command, parse_command
from trendalgo.botd.guard import FixedWindowLimiter, OwnerGuard
from trendalgo.botd.heartbeat import Heartbeat
from trendalgo.botd.host_store import HostStore, StalePlanError
from trendalgo.botd.outbox import Outbox
from trendalgo.botd.owner import ForeignOwnerError
from trendalgo.botd.pairing import PairingCodes
from trendalgo.trading.signed_command import now_seconds


def _json_object(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="body must be JSON") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    return value


def _ids(value: object) -> list[int]:
    if not isinstance(value, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in value
    ):
        raise HTTPException(status_code=400, detail="ids must be a list of integers")
    return value


def create_botd_app(
    *,
    store: HostStore,
    host_owner_id: str,
    nonce_db: Path,
    secret_provider: Callable[[], str | None],
    clock: Callable[[], int] = now_seconds,
    limiter: FixedWindowLimiter | None = None,
    secrets_root: Path | None = None,
) -> FastAPI:
    guard = OwnerGuard(
        owner_id=host_owner_id,
        nonce_db=nonce_db,
        secret_provider=secret_provider,
        limiter=limiter or FixedWindowLimiter(),
        clock=clock,
    )
    outbox = Outbox(store, host_owner_id=host_owner_id)
    heartbeat = Heartbeat(store)
    pairing = PairingCodes(store)
    vault_root = secrets_root if secrets_root is not None else store.db_path.parent
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/api/v1/status")
    async def status(request: Request) -> dict[str, Any]:
        await guard.require(request)
        plan = store.plan()
        return {
            "plan_version": int(plan["plan_version"]) if plan else 0,
            "bundle_hash": str(plan["bundle_hash"]) if plan else "",
            "positions": len(store.positions()),
            "pending_events": len(outbox.pending(limit=1000)),
            "last_beat": heartbeat.last_beat(),
        }

    @app.put("/api/v1/plan")
    async def put_plan(request: Request) -> dict[str, Any]:
        await guard.require(request)
        body = _json_object(await request.body())
        header, payload = body.get("header"), body.get("payload")
        if not isinstance(header, dict) or not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="header and payload must be objects")
        try:
            verified = verify_bundle(header, payload, host_owner_id=host_owner_id)
        except ForeignOwnerError as exc:
            raise HTTPException(
                status_code=403, detail="owner command refused: foreign_owner"
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"bundle refused: {exc}") from exc
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        try:
            store.save_plan(
                plan_version=verified.plan_version,
                bundle_hash=verified.bundle_hash,
                body=canonical,
            )
        except StalePlanError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"plan_version": verified.plan_version, "bundle_hash": verified.bundle_hash}

    @app.get("/api/v1/events")
    async def events(request: Request) -> dict[str, Any]:
        await guard.require(request)
        return {"events": outbox.pending()}

    @app.post("/api/v1/events/ack")
    async def ack(request: Request) -> dict[str, Any]:
        await guard.require(request)
        body = _json_object(await request.body())
        return {"removed": outbox.ack(_ids(body.get("ids")))}

    @app.post("/api/v1/pair")
    async def pair(request: Request) -> dict[str, Any]:
        await guard.require(request)
        body = _json_object(await request.body())
        code = body.get("code")
        if not isinstance(code, str) or not pairing.redeem(code, clock()):
            raise HTTPException(status_code=403, detail="pairing code refused")
        return {"paired": True}

    @app.post("/api/v1/commands")
    async def commands(request: Request) -> dict[str, Any]:
        await guard.require(request)
        body = _json_object(await request.body())
        try:
            action, bot_id, key = parse_command(body)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return apply_command(
            action=action,
            bot_id=bot_id,
            idempotency_key=key,
            outbox=outbox,
            owner_id=host_owner_id,
            now=clock(),
        )

    @app.put("/api/v1/telegram")
    async def put_telegram(request: Request) -> dict[str, Any]:
        """Device syncs BotFather credentials for cloud trade alerts (no PC required)."""
        await guard.require(request)
        from trendalgo.botd.telegram_secrets import save_creds, save_notify_flags

        body = _json_object(await request.body())
        token = body.get("bot_token")
        chat_id = body.get("chat_id")
        if not isinstance(token, str) or not token.strip():
            raise HTTPException(status_code=422, detail="bot_token required")
        if not isinstance(chat_id, str) and not isinstance(chat_id, int):
            raise HTTPException(status_code=422, detail="chat_id required")
        save_creds(vault_root, bot_token=token, chat_id=str(chat_id))
        trade_alerts = body.get("trade_alerts", True)
        telegram_enabled = body.get("telegram_enabled", True)
        telegram_trades = body.get("telegram_trades", True)
        save_notify_flags(
            vault_root,
            trade_alerts=bool(trade_alerts),
            telegram_enabled=bool(telegram_enabled),
            telegram_trades=bool(telegram_trades),
        )
        return {"saved": True}

    @app.get("/api/v1/portfolio")
    async def portfolio(request: Request) -> dict[str, Any]:
        """Read-only portfolio snapshot for the device Sync button (keys stay on host)."""
        await guard.require(request)
        from trendalgo.device.portfolio_sync import host_portfolio_payload

        path = store.db_path.parent / "portfolio.db"
        payload = host_portfolio_payload(path)
        if payload is None:
            return {"snapshot": None}
        return payload

    return app
