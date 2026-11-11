"""FastAPI application factory."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trendalgo.api.deps import require_owner
from trendalgo.api.routes import (
    ai_growth,
    auth_session,
    backtest,
    billing,
    bots,
    dashboard,
    debug,
    exchanges,
    export,
    health,
    hyperopt,
    icons,
    notifications,
    ops,
    pairs,
    platform,
    portfolio,
    portfolio_advanced,
    research,
    risk,
    scanner,
    signals,
    strategies,
    trading,
    watchlist,
    webhooks,
    ws,
)
from trendalgo.api.state import AppState, default_state
from trendalgo.bots.scheduler import start_bot_tick_scheduler
from trendalgo.exchanges.fee_scheduler import start_fee_scheduler
from trendalgo.exchanges.fee_store import get_fee_store
from trendalgo.exchanges.fee_sync import startup_fee_sync_background
from trendalgo.notifications.delivery import AlertDelivery
from trendalgo.portfolio.overview import build_portfolio_overview
from trendalgo.portfolio.snapshots import start_portfolio_scheduler
from trendalgo.scanner.scheduler import start_scheduler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def _cors_origins() -> list[str]:
    """Default empty — no browser client. Override with comma-separated origins."""
    raw = os.environ.get("TRENDALGO_CORS_ORIGINS", "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _shutdown_scheduler(scheduler: object | None) -> None:
    shutdown = getattr(scheduler, "shutdown", None)
    if callable(shutdown):
        shutdown(wait=False)


def create_app(state: AppState | None = None) -> FastAPI:
    app_state = state or default_state()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # AUTH-05: rotate bearer tokens on process start.
        app_state.bearer_store.clear()
        delivery = AlertDelivery(app_state.portfolio_store, on_log=app_state.log)
        scanner_sched = start_scheduler(
            app_state.scanner_store,
            app_state.log,
            delivery.deliver,
        )
        app_state.scanner_scheduler = scanner_sched
        portfolio_sched = start_portfolio_scheduler(
            app_state.portfolio_store,
            lambda: build_portfolio_overview(app_state),
            dry_run=app_state.bot.dry_run,
            on_log=app_state.log,
        )
        app_state.portfolio_scheduler = portfolio_sched
        fee_store = get_fee_store()
        startup_fee_sync_background(fee_store, on_log=app_state.log)
        fee_sched = start_fee_scheduler(fee_store, on_log=app_state.log)
        app_state.fee_scheduler = fee_sched
        bot_sched = start_bot_tick_scheduler(app_state)
        app_state.bot_scheduler = bot_sched
        yield
        if bot_sched is not None:
            await bot_sched.stop()
        _shutdown_scheduler(scanner_sched)
        _shutdown_scheduler(portfolio_sched)
        _shutdown_scheduler(fee_sched)

    app = FastAPI(title="TrendAlgo API", version="0.1.0", lifespan=lifespan)
    app.state.trendalgo = app_state

    origins = _cors_origins()
    # Credentials only with explicit origins — never with wildcard (AUTH-03).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = "/api/v1"
    owner = [Depends(require_owner)]
    # AUTH-01: require_owner at include time so new routes inherit it.
    app.include_router(health.router, prefix=prefix, tags=["health"], dependencies=owner)
    app.include_router(auth_session.router, prefix=prefix, tags=["auth"], dependencies=owner)
    app.include_router(pairs.router, prefix=prefix, tags=["pairs"], dependencies=owner)
    app.include_router(strategies.router, prefix=prefix, tags=["strategies"], dependencies=owner)
    app.include_router(backtest.router, prefix=prefix, tags=["backtest"], dependencies=owner)
    app.include_router(dashboard.router, prefix=prefix, tags=["dashboard"], dependencies=owner)
    app.include_router(risk.router, prefix=prefix, tags=["risk"], dependencies=owner)
    app.include_router(debug.router, prefix=prefix, tags=["debug"], dependencies=owner)
    app.include_router(
        notifications.router, prefix=prefix, tags=["notifications"], dependencies=owner
    )
    app.include_router(portfolio.router, prefix=prefix, tags=["portfolio"], dependencies=owner)
    app.include_router(
        portfolio_advanced.router,
        prefix=prefix,
        tags=["portfolio-advanced"],
        dependencies=owner,
    )
    app.include_router(exchanges.router, prefix=prefix, tags=["exchanges"], dependencies=owner)
    app.include_router(icons.router, prefix=prefix, tags=["icons"], dependencies=owner)
    app.include_router(platform.router, prefix=prefix, tags=["platform"], dependencies=owner)
    app.include_router(billing.router, prefix=prefix, tags=["billing"], dependencies=owner)
    app.include_router(ai_growth.router, prefix=prefix, tags=["ai-growth"], dependencies=owner)
    app.include_router(webhooks.router, prefix=prefix, tags=["webhooks"], dependencies=owner)
    app.include_router(ops.router, prefix=prefix, tags=["ops"], dependencies=owner)
    app.include_router(scanner.router, prefix=prefix, tags=["scanner"], dependencies=owner)
    app.include_router(bots.router, prefix=prefix, tags=["bots"], dependencies=owner)
    app.include_router(watchlist.router, prefix=prefix, tags=["watchlist"], dependencies=owner)
    app.include_router(signals.router, prefix=prefix, tags=["signals"], dependencies=owner)
    app.include_router(hyperopt.router, prefix=prefix, tags=["hyperopt"], dependencies=owner)
    app.include_router(research.router, prefix=prefix, tags=["research"], dependencies=owner)
    app.include_router(export.router, prefix=prefix, tags=["export"], dependencies=owner)
    app.include_router(trading.router, prefix=prefix, tags=["trading"], dependencies=owner)
    app.include_router(ws.router, prefix=prefix, tags=["ws"], dependencies=owner)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "trendalgo-api", "docs": "/docs"}

    return app
