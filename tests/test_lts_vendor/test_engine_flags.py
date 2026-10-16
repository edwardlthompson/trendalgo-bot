"""p2-engine-flags: trailing_stop_enabled (L2) and stake_mode/stake_value. Golden defaults stay put."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import pytest

from trendalgo.lts_vendor.backtesting.engine import run_backtest
from trendalgo.lts_vendor.backtesting.models import BacktestConfig

FEE_RATE = 52.0 / 10000.0 / 2.0  # side fee for the 52 bps round trip used by the config default


def _frame(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2026-09-01", periods=len(closes), freq="h")
    close = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )


def _signals(
    n: int, buy_at: tuple[int, ...] = (), sell_at: tuple[int, ...] = ()
) -> tuple[pd.Series, pd.Series]:
    idx = pd.date_range("2026-09-01", periods=n, freq="h")
    buy = pd.Series([i in buy_at for i in range(n)], index=idx, dtype=bool)
    sell = pd.Series([i in sell_at for i in range(n)], index=idx, dtype=bool)
    return buy, sell


def test_trailing_stop_is_on_by_default_and_fires_on_a_drop() -> None:
    frame = _frame([100.0, 110.0, 100.0])
    buy, sell = _signals(3)
    result = run_backtest(frame, buy, sell, BacktestConfig(trailing_stop_loss_pct=2.0))
    assert [t.exit_reason for t in result.trades] == ["trailing_stop_loss"]


def test_disabled_trailing_stop_never_fires_and_rides_to_end_of_data() -> None:
    frame = _frame([100.0, 110.0, 100.0])
    buy, sell = _signals(3)
    cfg = BacktestConfig(trailing_stop_enabled=False, trailing_stop_loss_pct=2.0)
    result = run_backtest(frame, buy, sell, cfg)
    assert [t.exit_reason for t in result.trades] == ["end_of_data"]


def test_disabled_trailing_stop_accepts_zero_but_enabled_still_needs_one_percent() -> None:
    BacktestConfig(trailing_stop_enabled=False, trailing_stop_loss_pct=0.0)
    with pytest.raises(ValueError, match="must be >= 1.0"):
        BacktestConfig(trailing_stop_enabled=True, trailing_stop_loss_pct=0.0)
    with pytest.raises(ValueError, match="must be >= 0"):
        BacktestConfig(trailing_stop_enabled=False, trailing_stop_loss_pct=-1.0)


def test_disabled_trailing_stop_setter_follows_the_same_floor() -> None:
    cfg = BacktestConfig(trailing_stop_enabled=False, trailing_stop_loss_pct=0.0)
    cfg.trailing_stop_pct = 0.5  # allowed while disabled
    cfg.trailing_stop_enabled = True
    with pytest.raises(ValueError, match="must be >= 1.0"):
        cfg.trailing_stop_pct = 0.5


def test_explicit_default_flags_match_the_default_config_exactly() -> None:
    rng = np.random.default_rng(7)
    closes = list(100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, 300))))
    frame = _frame(closes)
    buy, sell = _signals(300, buy_at=tuple(range(0, 300, 37)), sell_at=tuple(range(20, 300, 41)))
    default = run_backtest(frame, buy, sell, BacktestConfig())
    explicit = run_backtest(
        frame,
        buy,
        sell,
        BacktestConfig(trailing_stop_enabled=True, stake_mode="all_in", stake_value=None),
    )
    assert repr(explicit.final_equity) == repr(default.final_equity)
    assert [repr(t) for t in explicit.trades] == [repr(t) for t in default.trades]


def test_fixed_usd_stake_leaves_the_rest_of_the_cash_idle() -> None:
    frame = _frame([100.0] * 5)
    buy, sell = _signals(5)
    cfg = BacktestConfig(stake_mode="fixed_usd", stake_value=250.0)
    result = run_backtest(frame, buy, sell, cfg)
    trade = result.trades[0]
    assert trade.entry_fee + trade.quantity * trade.entry_price == pytest.approx(250.0)
    # 750 stayed idle while the 250 position round-tripped at a flat price.
    assert result.final_equity == pytest.approx(750.0 + 250.0 * (1 - FEE_RATE) ** 2)


def test_percent_stake_commits_that_share_of_free_cash() -> None:
    frame = _frame([100.0] * 5)
    buy, sell = _signals(5)
    result = run_backtest(frame, buy, sell, BacktestConfig(stake_mode="percent", stake_value=50))
    assert result.final_equity == pytest.approx(500.0 + 500.0 * (1 - FEE_RATE) ** 2)


def test_fixed_usd_stake_above_the_cash_is_the_whole_account() -> None:
    frame = _frame([100.0] * 5)
    buy, sell = _signals(5)
    capped = run_backtest(
        frame, buy, sell, BacktestConfig(stake_mode="fixed_usd", stake_value=5000.0)
    )
    all_in = run_backtest(frame, buy, sell, BacktestConfig())
    assert capped.final_equity == pytest.approx(all_in.final_equity)


def test_a_later_entry_restakes_free_cash_after_an_exit() -> None:
    frame = _frame([100.0] * 6)
    buy, sell = _signals(6, buy_at=(3,), sell_at=(1,))
    cfg = BacktestConfig(stake_mode="fixed_usd", stake_value=250.0)
    result = run_backtest(frame, buy, sell, cfg)
    assert [t.exit_reason for t in result.trades] == ["sell_signal", "end_of_data"]
    second = result.trades[1]
    assert second.entry_fee + second.quantity * second.entry_price == pytest.approx(250.0)
    # Free cash after round one is 750 idle plus 250 returned. Round two stakes 250 again.
    assert result.final_equity == pytest.approx(500.0 + 500.0 * (1 - FEE_RATE) ** 2)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"stake_mode": "martingale"}, "stake_mode must be one of"),
        ({"stake_mode": "fixed_usd"}, "stake_value must be a positive number"),
        ({"stake_mode": "fixed_usd", "stake_value": 0.0}, "stake_value must be a positive number"),
        ({"stake_mode": "fixed_usd", "stake_value": -5.0}, "stake_value must be a positive number"),
        (
            {"stake_mode": "fixed_usd", "stake_value": math.nan},
            "stake_value must be a positive number",
        ),
        (
            {"stake_mode": "percent", "stake_value": 150.0},
            "stake_value for percent must be at most 100",
        ),
        ({"stake_mode": "all_in", "stake_value": 50.0}, "stake_value applies only"),
    ],
)
def test_bad_stake_settings_are_refused(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BacktestConfig(**kwargs)
