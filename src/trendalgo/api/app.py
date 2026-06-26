"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trendalgo.api.routes import (
    backtest,
    backtest_library,
    ai_growth,
    billing,
    bots,
    dashboard,
    debug,
    health,
    hyperopt,
    notifications,
    ops,
    pairs,
    portfolio,
    portfolio_advanced,
    platform,
    export,
    exchanges,
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
from trendalgo.portfolio.overview import build_portfolio_overview
from trendalgo.portfolio.snapshots import start_portfolio_scheduler
from trendalgo.scanner.scheduler import start_scheduler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def _cors_origins() -> list[str]:
    raw = os.environ.get("TRENDALGO_CORS_ORIGINS", "*")
    return [part.strip() for part in raw.split(",") if part.strip()]


def create_app(state: AppState | None = None) -> FastAPI:
    app_state = state or default_state()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        scanner_sched = start_scheduler(app_state.scanner_store, app_state.log)
        app_state.scanner_scheduler = scanner_sched
        portfolio_sched = start_portfolio_scheduler(
            app_state.portfolio_store,
            lambda: build_portfolio_overview(app_state),
            dry_run=app_state.bot.dry_run,
            on_log=app_state.log,
        )
        app_state.portfolio_scheduler = portfolio_sched
        yield
        if scanner_sched is not None and hasattr(scanner_sched, "shutdown"):
            scanner_sched.shutdown(wait=False)
        if portfolio_sched is not None and hasattr(portfolio_sched, "shutdown"):
            portfolio_sched.shutdown(wait=False)

    app = FastAPI(title="TrendAlgo API", version="0.1.0", lifespan=lifespan)
    app.state.trendalgo = app_state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix, tags=["health"])
    app.include_router(pairs.router, prefix=prefix, tags=["pairs"])
    app.include_router(strategies.router, prefix=prefix, tags=["strategies"])
    app.include_router(backtest.router, prefix=prefix, tags=["backtest"])
    app.include_router(backtest_library.router, prefix=prefix, tags=["backtest-library"])
    app.include_router(dashboard.router, prefix=prefix, tags=["dashboard"])
    app.include_router(risk.router, prefix=prefix, tags=["risk"])
    app.include_router(debug.router, prefix=prefix, tags=["debug"])
    app.include_router(notifications.router, prefix=prefix, tags=["notifications"])
    app.include_router(portfolio.router, prefix=prefix, tags=["portfolio"])
    app.include_router(portfolio_advanced.router, prefix=prefix, tags=["portfolio-advanced"])
    app.include_router(exchanges.router, prefix=prefix, tags=["exchanges"])
    app.include_router(platform.router, prefix=prefix, tags=["platform"])
    app.include_router(billing.router, prefix=prefix, tags=["billing"])
    app.include_router(ai_growth.router, prefix=prefix, tags=["ai-growth"])
    app.include_router(webhooks.router, prefix=prefix, tags=["webhooks"])
    app.include_router(ops.router, prefix=prefix, tags=["ops"])
    app.include_router(scanner.router, prefix=prefix, tags=["scanner"])
    app.include_router(bots.router, prefix=prefix, tags=["bots"])
    app.include_router(watchlist.router, prefix=prefix, tags=["watchlist"])
    app.include_router(signals.router, prefix=prefix, tags=["signals"])
    app.include_router(hyperopt.router, prefix=prefix, tags=["hyperopt"])
    app.include_router(research.router, prefix=prefix, tags=["research"])
    app.include_router(export.router, prefix=prefix, tags=["export"])
    app.include_router(trading.router, prefix=prefix, tags=["trading"])
    app.include_router(ws.router, prefix=prefix, tags=["ws"])

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "trendalgo-api", "docs": "/docs"}

    return app
