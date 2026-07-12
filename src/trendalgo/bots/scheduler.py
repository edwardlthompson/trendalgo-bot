"""Async scheduled ticks for enabled bots."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any, Protocol

from trendalgo.billing.license_gate import check_license_gate
from trendalgo.bots.tick_candle import BotCandleLoader
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.runner.dry_run import DryRunRunner


class SchedulerState(Protocol):
    bot_orchestrator: Any
    risk_manager: Any
    exchange_control: Any
    billing_store: Any
    trade_journal: Any
    bot: Any
    portfolio_store: Any

    def log(self, message: str) -> None: ...


CandleLoader = Callable[[dict[str, Any]], Candle]


class BotTickScheduler:
    def __init__(
        self,
        state: SchedulerState,
        *,
        interval: float = 60.0,
        candle_loader: CandleLoader | None = None,
    ) -> None:
        self.state = state
        self.interval = max(0.1, interval)
        data_dir = state.bot_orchestrator.db_path.parent
        self._candle_loader = candle_loader or BotCandleLoader(data_dir)
        self._locks: dict[int, asyncio.Lock] = {}
        self._runners: dict[int, DryRunRunner] = {}
        self._last_candle: dict[int, int] = {}
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="trendalgo-bot-ticks")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def run_once(self) -> None:
        enabled = [bot for bot in self.state.bot_orchestrator.list_bots() if bot["enabled"]]
        await asyncio.gather(*(self.tick_bot(int(bot["id"])) for bot in enabled))

    async def tick_bot(self, bot_id: int) -> None:
        lock = self._locks.setdefault(bot_id, asyncio.Lock())
        if lock.locked():
            return
        async with lock:
            try:
                await self._guarded_tick(bot_id)
            except Exception as exc:
                message = f"bot tick failed bot_id={bot_id}: {exc}"
                self.state.log(message)
                try:
                    self.state.portfolio_store.insert_notification(
                        "trading", "Scheduled bot tick failed", message
                    )
                except Exception as inbox_exc:
                    self.state.log(f"bot tick error notification failed: {inbox_exc}")

    async def _guarded_tick(self, bot_id: int) -> None:
        bot = self.state.bot_orchestrator.get_bot(bot_id)
        if not bot or not bot["enabled"]:
            return
        risk_ok, risk_reason = self.state.risk_manager.can_open_trade()
        exchange_ok, exchange_reason = self.state.exchange_control.can_execute(
            str(bot["exchange"]), dry_run=bool(self.state.bot.dry_run)
        )
        license_ok, license_reason = check_license_gate(
            self.state.billing_store.get_enrollment(),
            self.state.billing_store.get_license_status(),
            dry_run=bool(self.state.bot.dry_run),
        )
        if not risk_ok or not exchange_ok or not license_ok:
            reason = next(
                reason
                for ok, reason in (
                    (risk_ok, risk_reason),
                    (exchange_ok, exchange_reason),
                    (license_ok, license_reason),
                )
                if not ok
            )
            self.state.log(f"bot tick blocked bot_id={bot_id}: {reason}")
            return
        candle = await asyncio.to_thread(self._candle_loader, bot)
        if self._last_candle.get(bot_id) == candle.timestamp_ms:
            return
        runner = self._runners.get(bot_id)
        if runner is None:
            runner = DryRunRunner(
                strategy=load_strategy(str(bot["strategy_id"])),
                journal=self.state.trade_journal,
                exchange_id=str(bot["exchange"]),
                pair=str(bot["pair"]),
                wallet_usd=float(bot["equity_usd"]),
                bot_id=bot_id,
                control=self.state.exchange_control,
            )
            self._runners[bot_id] = runner
        await asyncio.to_thread(runner.tick, candle)
        self._last_candle[bot_id] = candle.timestamp_ms

    async def _run(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.interval)


def start_bot_tick_scheduler(state: SchedulerState) -> BotTickScheduler | None:
    if os.environ.get("TRENDALGO_BOT_SCHEDULER_ENABLED", "1").lower() in {"0", "false", "no"}:
        return None
    interval = float(os.environ.get("TRENDALGO_BOT_TICK_SECONDS", "60"))
    scheduler = BotTickScheduler(state, interval=interval)
    scheduler.start()
    return scheduler
