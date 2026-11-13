"""Opportunity All-TA sauces only the Oracle top-N coins."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


def test_run_all_ta_sauces_only_top_oracle(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from trendalgo.device import scanner_all_ta_bt as mod

    coins = [
        {"symbol": "LOW", "pair": "LOW/USD"},
        {"symbol": "HIGH", "pair": "HIGH/USD"},
        {"symbol": "MID", "pair": "MID/USD"},
    ]
    pool_calls: list[dict[str, Any]] = []

    def fake_pool(
        batch: list[dict[str, Any]],
        *,
        include_sauce: bool,
        on_ok: Any,
        on_score: Any,
        seed_rows_by_symbol: dict[str, list[dict[str, Any]]] | None = None,
        **_k: Any,
    ) -> None:
        pool_calls.append(
            {
                "syms": [str(c["symbol"]) for c in batch],
                "include_sauce": include_sauce,
                "sauce_only": seed_rows_by_symbol is not None,
                "seed_syms": sorted((seed_rows_by_symbol or {}).keys()),
            }
        )
        for coin in batch:
            sym = str(coin["symbol"])
            oracle_net = {"HIGH": 30.0, "MID": 10.0, "LOW": 1.0}[sym]
            rows = [{"indicator": "Oracle max", "net_pct": oracle_net}]
            stats = {
                "tested": 1.0,
                "pruned": 0.0,
                "deepened": 1.0,
                "load_s": 0.0,
                "pass1_s": 0.1,
                "deepen_s": 0.1,
                "elapsed_s": 0.2,
            }
            on_ok(sym, rows, stats)
            if on_score is not None:
                on_score(sym, rows)

    class _RP:
        base_dir = str(tmp_path)
        scanner_db_path = str(tmp_path / "cache.db")
        cache_price_hours = 24
        backtest_fee_bps_round_trip = 52.0
        loader = object()

    monkeypatch.setattr(mod, "_run_pool", fake_pool)
    monkeypatch.setattr("trendalgo.lts_vendor.install_import_shims", lambda: None)

    # Avoid importing the real data_loader (needs api shim). Restore via monkeypatch.
    import sys
    import types

    bt_mod = types.ModuleType("trendalgo.lts_vendor.backtesting")
    dl_mod = types.ModuleType("trendalgo.lts_vendor.backtesting.data_loader")
    params_mod = types.ModuleType("trendalgo.lts_vendor.backtesting.params")
    shims_mod = types.ModuleType("trendalgo.lts_vendor.shims.database_cache")
    dl_mod.BacktestDataLoader = MagicMock  # type: ignore[attr-defined]
    params_mod.runner_params_from_settings = lambda: _RP()  # type: ignore[attr-defined]
    shims_mod.PriceCache = MagicMock  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "trendalgo.lts_vendor.backtesting", bt_mod)
    monkeypatch.setitem(sys.modules, "trendalgo.lts_vendor.backtesting.data_loader", dl_mod)
    monkeypatch.setitem(sys.modules, "trendalgo.lts_vendor.backtesting.params", params_mod)
    monkeypatch.setitem(sys.modules, "trendalgo.lts_vendor.shims.database_cache", shims_mod)

    monkeypatch.setattr(mod, "load_scan_bt_prefs", lambda _r: MagicMock(strategy_denylist=()))
    monkeypatch.setattr(mod, "enabled_strategies", lambda *_a, **_k: ("RSI",))
    monkeypatch.setattr(mod, "selected_timeframes", lambda *_a, **_k: ("1h",))
    monkeypatch.setattr(
        mod,
        "fee_for_exchange",
        lambda *_a, **_k: MagicMock(exchange_id="kraken", taker_pct=0.0026),
    )
    monkeypatch.setattr(mod, "needs_1m_base", lambda *_a, **_k: False)
    monkeypatch.setattr(mod, "all_ta_coin_workers", lambda: 2)
    monkeypatch.setattr(mod, "set_coin_parallel", lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "record_sample", lambda *_a, **_k: None)
    monkeypatch.setattr(mod, "get_scan_progress", lambda: MagicMock())
    monkeypatch.setattr(mod, "OPPORTUNITY_SAUCE_TOP_N", 2)

    out = mod.run_all_ta_scan_backtests(coins, prefs_root=tmp_path)
    assert out is not None
    # First run: top-2 + first-join LOW (never sauced).
    assert out["sauce_symbols"] == ["HIGH", "MID", "LOW"]
    assert len(pool_calls) == 2
    assert pool_calls[0]["include_sauce"] is False
    assert pool_calls[0]["sauce_only"] is False
    assert set(pool_calls[0]["syms"]) == {"HIGH", "MID", "LOW"}
    assert pool_calls[1]["include_sauce"] is True
    assert pool_calls[1]["sauce_only"] is True
    assert pool_calls[1]["syms"] == ["HIGH", "MID", "LOW"]
    assert set(pool_calls[1]["seed_syms"]) >= {"HIGH", "MID", "LOW"}

    # Second run: LOW already in sauce_ever → top-2 only.
    pool_calls.clear()
    out2 = mod.run_all_ta_scan_backtests(coins, prefs_root=tmp_path)
    assert out2 is not None
    assert out2["sauce_symbols"] == ["HIGH", "MID"]
    assert pool_calls[1]["syms"] == ["HIGH", "MID"]
