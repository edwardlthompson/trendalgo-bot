"""SIM-10: dry-run fills match paper fill/slip model."""

from __future__ import annotations

from trendalgo.trading.fill_model import paper_fill_price
from trendalgo.trading.runner.dry_run import DryRunRunner
from trendalgo.risk.journal import TradeJournal
from trendalgo.strategies.runtime.contract import Candle, Position, Signal, StrategyContext
from pathlib import Path


class _AlwaysEnter:
    strategy_id = "sim10"
    timeframe = "1m"

    @property
    def dataframe(self):  # noqa: ANN201
        import pandas as pd

        return pd.DataFrame()

    def on_candle(self, candle: Candle, ctx: StrategyContext) -> None:  # noqa: ARG002
        return None

    def signal(self, ctx: StrategyContext) -> Signal | None:
        if ctx.position is not None:
            return None
        return Signal(side="buy", stake_usd=100.0, rationale="sim10")

    def exit(self, ctx: StrategyContext, position: Position) -> bool:  # noqa: ARG002
        return False


def test_paper_fill_price_matches_entry_slip() -> None:
    assert paper_fill_price(100.0, side="buy", slippage_bps=100.0, fill_offset=0) == 101.0
    assert paper_fill_price(
        100.0, side="buy", slippage_bps=0.0, fill_offset=1, next_bar_price=105.0
    ) == 105.0


def test_dry_run_uses_shared_fill_model(tmp_path: Path) -> None:
    journal = TradeJournal(tmp_path / "j.db")
    runner = DryRunRunner(
        strategy=_AlwaysEnter(),
        journal=journal,
        exchange_id="kraken",
        pair="BTC/USD",
        fill_offset=1,
        slippage_bps=100.0,
    )
    # Signal on first candle; fill deferred to next bar close with slip.
    c0 = Candle(timestamp_ms=0, open=100, high=100, low=100, close=100, volume=1)
    c1 = Candle(timestamp_ms=60_000, open=110, high=110, low=110, close=110, volume=1)
    out0 = runner.tick(c0)
    assert "entry" not in out0["events"]
    out1 = runner.tick(c1)
    assert "entry" in out1["events"]
    assert runner._position is not None
    expected = paper_fill_price(110.0, side="buy", slippage_bps=100.0, fill_offset=0)
    assert abs(runner._position.entry_price - expected) < 1e-9
