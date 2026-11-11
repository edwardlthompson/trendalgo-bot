"""Shared application state for FastAPI (Sprint 3+)."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trendalgo.api.public_dashboard import PublicDashboardStore
from trendalgo.api.session_tokens import BearerTokenStore
from trendalgo.billing.store import BillingStore
from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.dex.control import DexVenueControlStore
from trendalgo.dex.nonce import NonceStore
from trendalgo.growth.store import GrowthStore
from trendalgo.notifications.telegram_ingress import TelegramIngress
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.risk.config import default_risk_limits
from trendalgo.risk.exit_rules import ExitRules, default_exit_rules
from trendalgo.risk.journal import TradeJournal
from trendalgo.risk.manager import RiskManager
from trendalgo.scanner.store import ScannerStore
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.watchlist.store import WatchlistStore


def _data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))


@dataclass
class BotSnapshot:
    dry_run: bool = True
    equity_usd: float = 1000.0
    open_trades: list[dict[str, Any]] = field(default_factory=list)
    open_orders: list[dict[str, Any]] = field(default_factory=list)
    bot_count: int = 1
    strategy_id: str = "multi-tf-example"
    pair: str = "BTC/USD"


@dataclass
class AppState:
    risk_manager: RiskManager
    bot: BotSnapshot
    strategy_params: dict[str, Any]
    portfolio_store: PortfolioStore
    scanner_store: ScannerStore
    bot_orchestrator: BotOrchestrator
    watchlist_store: WatchlistStore
    trade_journal: TradeJournal
    public_dashboard_store: PublicDashboardStore
    billing_store: BillingStore
    growth_store: GrowthStore
    exit_rules: ExitRules
    exchange_control: ExchangeControlStore
    dex_control: DexVenueControlStore
    dex_nonce_store: NonceStore
    data_dir: Path = field(default_factory=_data_dir)
    bearer_store: BearerTokenStore = field(default_factory=BearerTokenStore)
    telegram_ingress: TelegramIngress = field(default_factory=TelegramIngress)
    debug_logs: deque[str] = field(default_factory=lambda: deque(maxlen=500))
    last_backtest: dict[str, Any] | None = None
    last_ta_sweep: dict[str, Any] | None = None
    last_ta_fleet: dict[str, Any] | None = None
    scanner_scheduler: Any = None
    portfolio_scheduler: Any = None
    fee_scheduler: Any = None
    bot_scheduler: Any = None

    def log(self, message: str) -> None:
        self.debug_logs.appendleft(message)


def default_state() -> AppState:
    limits = default_risk_limits()
    wallet = 1000.0
    mgr = RiskManager(limits=limits, wallet_usd=wallet)
    data = _data_dir()
    return AppState(
        risk_manager=mgr,
        bot=BotSnapshot(
            dry_run=True,
            equity_usd=wallet,
            open_trades=[],
            open_orders=[],
        ),
        strategy_params={
            "rsi_entry": 35,
            "rsi_exit": 65,
            "lts_uniform_min": 0.55,
            "stoploss": -0.05,
        },
        portfolio_store=PortfolioStore(data / "portfolio.db"),
        scanner_store=ScannerStore(data / "scanner.db"),
        bot_orchestrator=BotOrchestrator(data / "bots.db"),
        watchlist_store=WatchlistStore(data / "watchlist.db"),
        trade_journal=TradeJournal(data / "journal.db"),
        public_dashboard_store=PublicDashboardStore(data / "public_dashboard.db"),
        billing_store=BillingStore(data / "billing.db"),
        growth_store=GrowthStore(data / "growth.db"),
        exit_rules=default_exit_rules(),
        data_dir=data,
        bearer_store=BearerTokenStore(),
        exchange_control=ExchangeControlStore(data / "exchange_control.db"),
        dex_control=DexVenueControlStore(data / "dex_control.db"),
        dex_nonce_store=NonceStore(data / "dex_nonces.json"),
    )
