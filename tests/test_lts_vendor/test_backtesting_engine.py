"""Core vendored backtesting engine / import-boundary smoke."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from trendalgo.lts_vendor import install_import_shims

FORBIDDEN_TOP = frozenset({"notifications", "main"})


def test_backtesting_import_guard() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "trendalgo" / "lts_vendor" / "backtesting"
    bad: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = (alias.name or "").split(".", 1)[0]
                    if top in FORBIDDEN_TOP:
                        bad.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                top = base.split(".", 1)[0] if base else ""
                level = getattr(node, "level", 0) or 0
                if top in FORBIDDEN_TOP and level == 0:
                    bad.append(f"{path.name}: from {base}")
    assert not bad, bad


def test_engine_buy_and_hold_and_rsi() -> None:
    install_import_shims()
    from trendalgo.lts_vendor.backtesting.engine import compute_buy_and_hold, run_backtest
    from trendalgo.lts_vendor.backtesting.models import BacktestConfig
    from trendalgo.lts_vendor.backtesting.signals import generate_indicator_signals

    idx = pd.date_range("2024-01-01", periods=120, freq="h", tz="UTC")
    close = pd.Series([100 + i * 0.2 + (5 if i % 20 == 0 else 0) for i in range(120)], index=idx)
    frame = pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000.0,
        },
        index=idx,
    )
    cfg = BacktestConfig(
        starting_capital=1000.0,
        fee_bps_round_trip=20.0,
        trailing_stop_loss_pct=6.0,
    )
    bh = compute_buy_and_hold(frame, cfg)
    assert bh.final_equity > 0
    entries, exits = generate_indicator_signals(
        "RSI", frame, {"period": 14, "lower": 30, "upper": 70}
    )
    assert len(entries) == len(frame)
    result = run_backtest(frame, entries, exits, cfg)
    assert result.final_equity > 0


def test_synthetic_loader_returns_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    # Offline and deterministic: no live Kraken call; the opt-in flag enables the synthetic branch.
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setenv("BACKTEST_ALLOW_SYNTHETIC", "1")
    install_import_shims()
    from trendalgo.lts_vendor.shims import api_coingecko as cg

    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: None)
    from trendalgo.lts_vendor.backtesting.data_loader import BacktestDataLoader
    from trendalgo.lts_vendor.backtesting.params import BacktestLoaderParams
    from trendalgo.lts_vendor.shims.database_cache import PriceCache

    lp = BacktestLoaderParams(
        coingecko_calls_per_minute=30,
        cmc_api_key="",
        cmc_calls_per_minute=30,
        polygon_calls_per_minute=5,
        ohlcv_min_1h_bars_per_day=20,
        ohlcv_min_1h_bars_slack=2,
        ohlcv_min_1h_bars_floor=48,
        ohlcv_min_1d_bars_slack=2,
        ohlcv_min_1d_bars_floor=14,
    )
    loader = BacktestDataLoader(cache=PriceCache(), loader_params=lp)
    loaded = loader.load("BTC", timeframe="1h", days=30, gecko_id="bitcoin")
    assert loaded.frame is not None
    assert len(loaded.frame) >= 48
