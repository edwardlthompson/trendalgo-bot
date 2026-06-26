"""Dry-run native trading runner — simulated fills → journal (CM-1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.strategies.runtime.contract import Candle, NativeStrategy, Position, Signal, StrategyContext
from trendalgo.trading.control import ExchangeControlStore
from trendalgo.trading.runner.adapters.registry import get_trading_adapter


@dataclass
class DryRunOrder:
    pair: str
    side: str
    stake_usd: float
    price: float
    exchange_id: str
    simulated: bool = True
    order_id: str = ""


@dataclass
class DryRunRunner:
    """Simulate one bot on a single exchange — create/cancel orders only (CM-7)."""

    strategy: NativeStrategy
    journal: TradeJournal
    exchange_id: str = "kraken"
    pair: str = "BTC/USD"
    wallet_usd: float = 1000.0
    bot_id: int | None = None
    control: ExchangeControlStore | None = None
    _position: Position | None = field(default=None, init=False)
    _last_orders: list[DryRunOrder] = field(default_factory=list, init=False)

    def tick(
        self,
        candle: Candle,
        *,
        informative_candles: list[Candle] | None = None,
    ) -> dict[str, Any]:
        """Process one candle: update indicators, evaluate exit/entry, journal fills."""
        import pandas as pd

        if self.control is not None:
            ok, reason = self.control.can_execute(self.exchange_id, dry_run=True)
            if not ok:
                return {
                    "engine": "native",
                    "exchange_id": self.exchange_id,
                    "pair": self.pair,
                    "blocked": True,
                    "block_reason": reason,
                    "events": [],
                    "position_open": self._position is not None,
                    "orders": [],
                }

        informative_df = None
        if informative_candles:
            informative_df = pd.DataFrame(
                [
                    {
                        "timestamp_ms": c.timestamp_ms,
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume,
                    }
                    for c in informative_candles
                ]
            )

        ctx = StrategyContext(
            pair=self.pair,
            timeframe=self.strategy.timeframe,
            dataframe=self.strategy.dataframe if hasattr(self.strategy, "dataframe") else pd.DataFrame(),
            position=self._position,
            wallet_usd=self.wallet_usd,
            informative_df=informative_df,
            metadata={"exchange_id": self.exchange_id, "engine": "native", "bot_id": self.bot_id},
        )
        self.strategy.on_candle(candle, ctx)
        events: list[str] = []

        if self._position is not None and self.strategy.exit(ctx, self._position):
            pnl = self._close_position(candle.close)
            events.append("exit")
            if pnl is not None:
                events.append(f"pnl={pnl:.2f}")

        if self._position is None:
            sig = self.strategy.signal(ctx)
            if sig is not None:
                self._open_position(sig, candle.close)
                events.append("entry")

        return {
            "engine": "native",
            "exchange_id": self.exchange_id,
            "pair": self.pair,
            "bot_id": self.bot_id,
            "events": events,
            "position_open": self._position is not None,
            "orders": [o.__dict__ for o in self._last_orders],
        }

    def _open_position(self, sig: Signal, price: float) -> None:
        adapter = get_trading_adapter(self.exchange_id)
        routed = adapter.simulate_order(self.pair, sig.side, sig.stake_usd, price)
        order = DryRunOrder(
            pair=self.pair,
            side=sig.side,
            stake_usd=sig.stake_usd,
            price=price,
            exchange_id=self.exchange_id,
            order_id=str(routed.get("order_id", "")),
        )
        self._last_orders = [order]
        self._position = Position(
            pair=self.pair,
            side=sig.side,
            stake_usd=sig.stake_usd,
            entry_price=price,
        )
        self.journal.append_trade(
            TradeRecord(
                pair=self.pair,
                side=sig.side,
                stake_usd=sig.stake_usd,
                pnl_usd=0.0,
                signal_source=self.strategy.strategy_id,
                rationale=sig.rationale,
                exchange_trade_id=str(routed.get("order_id", "")),
                exchange=self.exchange_id,
                bot_id=self.bot_id,
            )
        )

    def _close_position(self, price: float) -> float | None:
        if self._position is None:
            return None
        pos = self._position
        ratio = (price - pos.entry_price) / pos.entry_price if pos.entry_price else 0.0
        pnl = pos.stake_usd * ratio
        adapter = get_trading_adapter(self.exchange_id)
        routed = adapter.simulate_order(self.pair, "sell", pos.stake_usd, price)
        self.journal.append_trade(
            TradeRecord(
                pair=self.pair,
                side="sell",
                stake_usd=pos.stake_usd,
                pnl_usd=pnl,
                signal_source=self.strategy.strategy_id,
                rationale="native exit",
                exchange_trade_id=str(routed.get("order_id", "")),
                exchange=self.exchange_id,
                bot_id=self.bot_id,
            )
        )
        self._position = None
        self._last_orders = [
            DryRunOrder(
                pair=self.pair,
                side="sell",
                stake_usd=pos.stake_usd,
                price=price,
                exchange_id=self.exchange_id,
                order_id=str(routed.get("order_id", "")),
            )
        ]
        return pnl
