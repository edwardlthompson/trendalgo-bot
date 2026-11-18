"""Catalog Market Context must survive Sauce-only meta payloads."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


def test_run_pool_on_ctx_ignores_sauce_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device import scanner_all_ta_pool as pool

    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_coin(
        coin: dict[str, Any],
        **_k: Any,
    ) -> tuple[str, list[dict[str, Any]], dict[str, float], dict[str, Any] | None]:
        sym = str(coin["symbol"])
        # Sauce-only style meta (no "ok") must not reach on_ctx.
        return sym, [], {"elapsed_s": 0.0}, {"sauce_only": True, "phase_s": {}}

    monkeypatch.setattr(pool, "backtest_one_coin", fake_coin)
    progress = MagicMock()
    pool.run_pool(
        [{"symbol": "BTC", "pair": "BTC/USD"}],
        workers=1,
        include_sauce=True,
        loader_factory=MagicMock,
        timeframes=("1h",),
        strat_list=("RSI",),
        stake=1000.0,
        fee=MagicMock(),
        fee_bps=52.0,
        prefs_root=MagicMock(),
        progress=progress,
        on_ok=lambda *_a: None,
        on_ctx=lambda sym, ctx: calls.append((sym, ctx)),
        on_score=None,
        include_market_context=False,
    )
    assert calls == []


def test_run_pool_on_ctx_keeps_real_market_context(monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device import scanner_all_ta_pool as pool

    calls: list[tuple[str, dict[str, Any]]] = []
    real = {"ok": True, "consensus": {"signal": "Buy", "score": 1.0, "confidence": 50.0}}

    def fake_coin(
        coin: dict[str, Any],
        **_k: Any,
    ) -> tuple[str, list[dict[str, Any]], dict[str, float], dict[str, Any] | None]:
        return str(coin["symbol"]), [], {"elapsed_s": 0.0}, real

    monkeypatch.setattr(pool, "backtest_one_coin", fake_coin)
    progress = MagicMock()
    pool.run_pool(
        [{"symbol": "ETH", "pair": "ETH/USD"}],
        workers=1,
        include_sauce=False,
        loader_factory=MagicMock,
        timeframes=("1h",),
        strat_list=("RSI",),
        stake=1000.0,
        fee=MagicMock(),
        fee_bps=52.0,
        prefs_root=MagicMock(),
        progress=progress,
        on_ok=lambda *_a: None,
        on_ctx=lambda sym, ctx: calls.append((sym, ctx)),
        on_score=None,
        include_market_context=True,
    )
    assert calls == [("ETH", real)]


def test_sauce_pool_passes_include_market_context_false(monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device import scanner_all_ta_pool as pool

    seen: dict[str, Any] = {}

    def fake_run_pool(*_a: Any, **kwargs: Any) -> None:
        seen.update(kwargs)

    monkeypatch.setattr(pool, "run_pool", fake_run_pool)
    monkeypatch.setattr(pool, "set_coin_parallel", lambda *_a, **_k: None)
    monkeypatch.setattr(pool, "parallel_log_bits", lambda: "x")
    ok = pool.sauce_pool_on_seeds(
        [{"symbol": "BTC"}],
        loader_factory=MagicMock,
        timeframes=("1h",),
        strat_list=("RSI",),
        stake=1000.0,
        fee=MagicMock(),
        fee_bps=52.0,
        prefs_root=MagicMock(),
        progress=MagicMock(),
        seed_rows_by_symbol={"BTC": []},
        on_ok=lambda *_a: None,
        on_ctx=lambda *_a: None,
    )
    assert ok is True
    assert seen.get("include_market_context") is False
