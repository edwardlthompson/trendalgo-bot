"""R5: entries are gated and exits never are. R4: an over-cap plan blocks entries on each pass."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from trendalgo.bots import scheduler as scheduler_module
from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.bots.scheduler import BotTickScheduler
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal
from trendalgo.risk.manager import RiskManager
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.trading.control import ExchangeControlStore


class HoldingRunner:
    """Stands in for DryRunRunner: a flat runner opens on tick, a held one closes on tick."""

    entries = 0
    exits = 0

    def __init__(self, **_kwargs: Any) -> None:
        self.holding = False

    def tick(self, _candle: Candle) -> dict[str, Any]:
        if self.holding:
            self.holding = False
            HoldingRunner.exits += 1
        else:
            self.holding = True
            HoldingRunner.entries += 1
        return {"position_open": self.holding}


def _new_candles() -> Any:
    counter = {"n": 0}

    def load(_bot: dict[str, Any]) -> Candle:
        counter["n"] += 1
        return Candle(timestamp_ms=counter["n"], open=1, high=2, low=1, close=2, volume=1)

    return load


@pytest.fixture(autouse=True)
def _fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    HoldingRunner.entries = 0
    HoldingRunner.exits = 0
    monkeypatch.setattr(scheduler_module, "DryRunRunner", HoldingRunner)
    monkeypatch.setattr(scheduler_module, "load_strategy", lambda _id: object())
    monkeypatch.setattr(scheduler_module, "check_license_gate", lambda *_a, **_k: (True, "ok"))


def _state(tmp_path: Path, wallet_usd: float = 10_000.0) -> SimpleNamespace:
    logs: list[str] = []
    return SimpleNamespace(
        bot_orchestrator=BotOrchestrator(tmp_path / "bots.db"),  # H1: no seeded bot
        risk_manager=RiskManager(RiskLimits(), wallet_usd=wallet_usd),
        exchange_control=ExchangeControlStore(tmp_path / "exchange.db"),
        billing_store=SimpleNamespace(get_enrollment=lambda: {}, get_license_status=lambda: {}),
        trade_journal=TradeJournal(tmp_path / "journal.db"),
        bot=SimpleNamespace(dry_run=True),
        portfolio_store=PortfolioStore(tmp_path / "portfolio.db"),
        log=logs.append,
        logs=logs,
    )


def test_a_flat_bot_with_gates_open_enters_then_exits(tmp_path: Path) -> None:
    state = _state(tmp_path)
    bot_id = state.bot_orchestrator.add_bot("flat", "s", "BTC/USD", equity_usd=1000)
    scheduler = BotTickScheduler(state, candle_loader=_new_candles())
    asyncio.run(scheduler.tick_bot(bot_id))
    asyncio.run(scheduler.tick_bot(bot_id))
    assert (HoldingRunner.entries, HoldingRunner.exits) == (1, 1)


def test_a_flat_bot_with_the_breaker_tripped_does_not_enter(tmp_path: Path) -> None:
    state = _state(tmp_path)
    bot_id = state.bot_orchestrator.add_bot("flat", "s", "BTC/USD", equity_usd=1000)
    state.risk_manager.state.circuit_breaker_active = True
    scheduler = BotTickScheduler(state, candle_loader=_new_candles())
    asyncio.run(scheduler.tick_bot(bot_id))
    assert HoldingRunner.entries == 0
    assert any("circuit breaker active" in line for line in state.logs)


def test_a_held_bot_still_exits_with_breaker_tripped_and_license_suspended(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    bot_id = state.bot_orchestrator.add_bot("held", "s", "BTC/USD", equity_usd=1000)
    scheduler = BotTickScheduler(state, candle_loader=_new_candles())
    asyncio.run(scheduler.tick_bot(bot_id))  # opens while the gates are open
    assert HoldingRunner.entries == 1

    state.risk_manager.state.circuit_breaker_active = True
    monkeypatch.setattr(
        scheduler_module, "check_license_gate", lambda *_a, **_k: (False, "license suspended")
    )
    asyncio.run(scheduler.tick_bot(bot_id))  # gates blocked, position still held
    assert HoldingRunner.exits == 1
    assert HoldingRunner.entries == 1  # no new entry while blocked
    assert any("exits still run" in line for line in state.logs)


def test_an_over_cap_plan_blocks_entries_on_each_pass(tmp_path: Path) -> None:
    state = _state(tmp_path, wallet_usd=5000)  # 5,000 x 0.8 = 4,000 allowed
    state.bot_orchestrator.add_bot("a", "s", "BTC/USD", equity_usd=4000)
    state.bot_orchestrator.add_bot("b", "s", "ETH/USD", equity_usd=3000)
    scheduler = BotTickScheduler(state, candle_loader=_new_candles())
    asyncio.run(scheduler.run_once())
    assert HoldingRunner.entries == 0
    assert any("allocation rejected" in line for line in state.logs)
