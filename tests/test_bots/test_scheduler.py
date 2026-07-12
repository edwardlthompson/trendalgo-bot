import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.bots.scheduler import BotTickScheduler
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.trading.control import ExchangeControlStore


class FakeRunner:
    ticks = 0

    def __init__(self, **_kwargs: Any) -> None:
        pass

    def tick(self, _candle: Candle) -> dict[str, object]:
        FakeRunner.ticks += 1
        return {}


def make_state(tmp_path: Path) -> SimpleNamespace:
    logs: list[str] = []
    return SimpleNamespace(
        bot_orchestrator=BotOrchestrator(tmp_path / "bots.db"),
        risk_manager=RiskManager(RiskLimits(), wallet_usd=1000),
        exchange_control=ExchangeControlStore(tmp_path / "exchange.db"),
        billing_store=SimpleNamespace(
            get_enrollment=lambda: {},
            get_license_status=lambda: {},
        ),
        trade_journal=object(),
        bot=SimpleNamespace(dry_run=True),
        portfolio_store=PortfolioStore(tmp_path / "portfolio.db"),
        log=logs.append,
        logs=logs,
    )


def candle(_bot: dict[str, Any]) -> Candle:
    return Candle(timestamp_ms=1, open=1, high=2, low=1, close=2, volume=1)


def test_scheduler_ticks_enabled_bot_and_rechecks_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = make_state(tmp_path)
    FakeRunner.ticks = 0
    monkeypatch.setattr("trendalgo.bots.scheduler.DryRunRunner", FakeRunner)
    monkeypatch.setattr("trendalgo.bots.scheduler.load_strategy", lambda _strategy_id: object())
    scheduler = BotTickScheduler(state, candle_loader=candle)

    asyncio.run(scheduler.run_once())
    assert FakeRunner.ticks == 1

    state.risk_manager.pause()
    asyncio.run(scheduler.tick_bot(1))
    assert FakeRunner.ticks == 1
    assert any("trading paused" in line for line in state.logs)


def test_tick_error_isolated_and_written_to_inbox(tmp_path: Path) -> None:
    state = make_state(tmp_path)

    def fail(_bot: dict[str, Any]) -> Candle:
        raise TimeoutError("market timeout")

    scheduler = BotTickScheduler(state, candle_loader=fail)
    asyncio.run(scheduler.run_once())

    inbox = state.portfolio_store.list_notifications()
    assert inbox[0]["title"] == "Scheduled bot tick failed"
    assert "market timeout" in str(inbox[0]["body"])
