"""Hill-climb deepen keeps or improves seed; all indicators get numeric axes."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.hill_climb import SIGNAL_TSL, climb_seed
from trendalgo.backtest.hill_climb_axes import climb_axes, seed_params
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _ohlcv(n: int = 120) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    # Oscillating close so RSI can trade.
    close = pd.Series([100 + ((i % 20) - 10) * 2 for i in range(n)], index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 100.0,
        },
        index=idx,
    )


def test_climb_seed_rsi_includes_levels(monkeypatch: Any) -> None:
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    calls: list[str] = []
    seed = {
        "strategy_id": "RSI",
        "net_profit": 1.0,
        "params": {"timeperiod": 14, "entry_level": 30, "exit_level": 70},
        "trailing_stop_pct": 0.0,
    }

    def fake_trial(
        _frame: Any,
        sid: str,
        params: dict[str, Any],
        tsl: float,
        **_k: Any,
    ) -> dict[str, Any] | None:
        # Prefer entry_level=25 so climb walks there.
        entry = float(params.get("entry_level") or 30)
        net = 10.0 - abs(entry - 25.0) + (tsl * 100.0) * 0.1
        return {
            "strategy_id": sid,
            "net_profit": net,
            "trades": 3,
            "win_rate": 0.6,
            "params": dict(params),
            "trailing_stop_pct": tsl,
            "timeframe": "1h",
            "tsl_hits": 0,
        }

    monkeypatch.setattr("trendalgo.backtest.hill_climb._trial", fake_trial)
    # Force TSL grid to use trial_fn (not real signal accel) so the fake reward applies.
    monkeypatch.setattr(
        "trendalgo.backtest.hill_climb_tsl.prepare_signals",
        lambda *_a, **_k: (None, None, None),
    )
    best = climb_seed(
        _ohlcv(),
        seed,
        fee=fee,
        stake_usd=1000.0,
        timeframe="1h",
        on_progress=calls.append,
    )
    assert best is not None
    assert float(best["net_profit"]) >= float(seed["net_profit"])
    params = best["params"]
    assert "entry_level" in params
    assert "exit_level" in params
    assert all(isinstance(v, int) for v in params.values())
    # Fake trial rewards wider TSL, so Stage D should pick a trail > signal-only.
    assert float(best["trailing_stop_pct"]) > SIGNAL_TSL
    assert int(params["entry_level"]) == 25
    assert any("params" in line or "TSL" in line for line in calls)


def test_climb_seed_keeps_signal_when_trails_do_not_help(monkeypatch: Any) -> None:
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    seed = {
        "strategy_id": "RSI",
        "net_profit": 1.0,
        "params": {"timeperiod": 14, "entry_level": 30, "exit_level": 70},
        "trailing_stop_pct": 0.0,
        "timeframe": "1h",
        "trades": 5,
    }

    def fake_trial(
        _frame: Any,
        sid: str,
        params: dict[str, Any],
        tsl: float,
        **_k: Any,
    ) -> dict[str, Any] | None:
        # Trails always worse than signal-only.
        net = 10.0 - abs(float(params.get("entry_level") or 30) - 25.0) - (tsl * 100.0)
        return {
            "strategy_id": sid,
            "net_profit": net,
            "trades": 5,
            "win_rate": 0.8,
            "params": dict(params),
            "trailing_stop_pct": tsl,
            "timeframe": "1h",
            "tsl_hits": 0,
        }

    monkeypatch.setattr("trendalgo.backtest.hill_climb._trial", fake_trial)
    monkeypatch.setattr(
        "trendalgo.backtest.hill_climb_tsl.prepare_signals",
        lambda *_a, **_k: (None, None, None),
    )
    best = climb_seed(_ohlcv(), seed, fee=fee, stake_usd=1000.0, timeframe="1h")
    assert best is not None
    # Signal-only still wins the net race, but Results never keep TSL=0 —
    # plateau pick stamps the lowest unhit trail (+ breath when tied).
    assert float(best["trailing_stop_pct"]) > 0.0
    assert float(best["trailing_stop_pct"]) >= 0.01


def test_climb_axes_cover_macd_and_bounded_levels() -> None:
    macd = seed_params("MACD", None)
    macd_keys = {key for key, *_rest in climb_axes("MACD", macd)}
    assert {"fastperiod", "slowperiod", "signalperiod"} <= macd_keys
    cci = seed_params("CCI", None)
    cci_keys = {key for key, *_rest in climb_axes("CCI", cci)}
    assert "timeperiod" in cci_keys
    assert "entry_level" in cci_keys
    assert "exit_level" in cci_keys
