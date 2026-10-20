"""Async scheduled ticks for enabled bots. Entries are gated; exits never are (R4, R5)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

from trendalgo.billing.license_gate import check_license_gate
from trendalgo.bots.first_bot_rails import FirstBotRails, reject_entry_reason
from trendalgo.bots.tick_candle import BotCandleLoader
from trendalgo.risk.allocation import allocation_error
from trendalgo.risk.manager import utc_day_start
from trendalgo.risk.strategy_mixins import RiskGuardMixin
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.entry_cooldown import CooldownConfig, can_enter
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
        self._holding: dict[int, bool] = {}
        self._last_candle: dict[int, int] = {}
        self._allocation_block: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._last_sell_bar_ms: dict[int, int] = {}
        self._entries_hour: dict[int, list[float]] = {}
        self._rails = FirstBotRails()
        self._cooldown_by_bot: dict[int, CooldownConfig] = {}

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
        self._refresh_host_state(enabled)
        await asyncio.gather(*(self.tick_bot(int(bot["id"])) for bot in enabled))

    def _refresh_host_state(self, enabled: list[dict[str, Any]]) -> None:
        """Once per pass: today's PnL from journaled fills (R2) and the plan's allocation (R4)."""
        risk = self.state.risk_manager
        now = datetime.now(UTC)
        risk.sync_daily_pnl(
            self.state.trade_journal.realized_pnl_since(utc_day_start(now).isoformat()), now
        )
        self._allocation_block = allocation_error(
            [float(bot["equity_usd"]) for bot in enabled],
            risk.wallet_usd,
            risk.limits.max_exposure_pct,
        )

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

    def _entry_block(self, bot: dict[str, Any], *, now_ms: int | None = None) -> str | None:
        """Why new entries are blocked for this bot, or None. Exits are never blocked here (R5)."""
        dry = bool(self.state.bot.dry_run)
        bot_id = int(bot["id"])
        checks = (
            self.state.risk_manager.can_open_trade(),
            self.state.exchange_control.can_execute(str(bot["exchange"]), dry_run=dry),
            check_license_gate(
                self.state.billing_store.get_enrollment(),
                self.state.billing_store.get_license_status(),
                dry_run=dry,
            ),
            (self._allocation_block is None, self._allocation_block or "allocation ok"),
        )
        blocked = next((reason for ok, reason in checks if not ok), None)
        if blocked is not None:
            return blocked
        tf = str(bot.get("timeframe") or "1h")
        cooldown = self._cooldown_by_bot.get(bot_id) or CooldownConfig(timeframe=tf)
        clock = now_ms if now_ms is not None else int(datetime.now(UTC).timestamp() * 1000)
        ok_cd, reason_cd = can_enter(
            last_sell_bar_open_ms=self._last_sell_bar_ms.get(bot_id),
            now_ms=clock,
            config=cooldown,
        )
        if not ok_cd:
            return reason_cd
        stamps = self._entries_hour.setdefault(bot_id, [])
        cutoff = clock / 1000.0 - 3600.0
        stamps[:] = [t for t in stamps if t >= cutoff]
        rail = reject_entry_reason(
            rails=self._rails,
            open_trades=1 if self._holding.get(bot_id) else 0,
            entries_last_hour=len(stamps),
            seconds_since_last_exit=None,
            fee_pct_of_stake=0.0,
        )
        return rail

    async def _guarded_tick(self, bot_id: int) -> None:
        bot = self.state.bot_orchestrator.get_bot(bot_id)
        if not bot or not bot["enabled"]:
            return
        block = self._entry_block(bot)
        if block is not None and not self._holding.get(bot_id, False):
            self.state.log(f"bot tick blocked bot_id={bot_id}: {block}")
            return
        candle = await asyncio.to_thread(self._candle_loader, bot)
        if self._last_candle.get(bot_id) == candle.timestamp_ms:
            return
        runner = self._runners.get(bot_id)
        if runner is None:
            strategy = load_strategy(str(bot["strategy_id"]))
            if isinstance(strategy, RiskGuardMixin):
                strategy.risk_manager = self.state.risk_manager  # the one host manager (R3)
            runner = DryRunRunner(
                strategy=strategy,
                journal=self.state.trade_journal,
                exchange_id=str(bot["exchange"]),
                pair=str(bot["pair"]),
                wallet_usd=float(bot["equity_usd"]),
                bot_id=bot_id,
                control=self.state.exchange_control,
            )
            self._runners[bot_id] = runner
        if block is not None:
            # A held position can only exit: the runner opens no second one (R5).
            self.state.log(f"entries blocked bot_id={bot_id}: {block}; exits still run")
        was_holding = self._holding.get(bot_id, False)
        result = await asyncio.to_thread(runner.tick, candle)
        now_holding = bool(result.get("position_open", False))
        if was_holding and not now_holding:
            self._last_sell_bar_ms[bot_id] = candle.timestamp_ms
        if not was_holding and now_holding:
            self._entries_hour.setdefault(bot_id, []).append(candle.timestamp_ms / 1000.0)
        self._holding[bot_id] = now_holding
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
