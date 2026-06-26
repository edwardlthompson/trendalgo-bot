"""Native backtest adapter — S7 library integration (CM-1)."""

from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from trendalgo.risk.journal import TradeJournal
from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary
from trendalgo.strategies.runtime.contract import Candle, NativeStrategy
from trendalgo.trading.runner.dry_run import DryRunRunner


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC).replace(microsecond=0)


def run_native_backtest(
    strategy: NativeStrategy,
    candles: list[Candle],
    *,
    pair: str,
    exchange_id: str = "kraken",
    informative_candles: list[Candle] | None = None,
    initial_wallet: float = 1000.0,
    timerange: str = "native",
    journal: TradeJournal | None = None,
) -> BacktestResult:
    """Walk candles through native strategy hooks; return BacktestResult."""
    owns_journal = journal is None
    db_path = Path(tempfile.gettempdir()) / f"trendalgo-native-bt-{uuid.uuid4().hex}.db"
    if journal is None:
        journal = TradeJournal(db_path)
    runner = DryRunRunner(
        strategy=strategy,
        journal=journal,
        exchange_id=exchange_id,
        pair=pair,
        wallet_usd=initial_wallet,
    )
    open_at: datetime | None = None
    open_stake = 0.0
    trades: list[BacktestTradeSummary] = []
    peak = initial_wallet
    max_dd = 0.0
    equity = initial_wallet

    try:
        for candle in candles:
            info_slice = None
            if informative_candles:
                info_slice = [
                    c for c in informative_candles if c.timestamp_ms <= candle.timestamp_ms
                ]
            runner.tick(candle, informative_candles=info_slice)
            if runner._position is not None and open_at is None:
                open_at = _ms_to_dt(candle.timestamp_ms)
                open_stake = runner._position.stake_usd
            elif runner._position is None and open_at is not None:
                last = journal.list_trades(limit=1)
                pnl = float(last[0]["pnl_usd"]) if last else 0.0
                trades.append(
                    BacktestTradeSummary(
                        pair=pair,
                        profit_ratio=pnl / open_stake if open_stake else 0.0,
                        profit_abs=pnl,
                        open_date=open_at,
                        close_date=_ms_to_dt(candle.timestamp_ms),
                    )
                )
                equity += pnl
                peak = max(peak, equity)
                if peak > 0:
                    max_dd = max(max_dd, (peak - equity) / peak)
                open_at = None
                open_stake = 0.0
    finally:
        del runner
        if owns_journal:
            del journal
            try:
                db_path.unlink(missing_ok=True)
            except OSError:
                pass

    profit_total = sum(t.profit_abs for t in trades)
    return BacktestResult(
        strategy=strategy.strategy_id,
        pair=pair,
        timeframe=strategy.timeframe,
        timerange=timerange,
        total_trades=len(trades),
        profit_total=profit_total,
        profit_total_pct=round(profit_total / initial_wallet, 4) if initial_wallet else 0.0,
        max_drawdown=round(max_dd, 4) if trades else None,
        trades=trades,
        metadata={"engine": "native", "exchange_id": exchange_id, "candles": len(candles)},
    )
