"""Edge coverage for CDL/structure bank, Oracle-first refine, peer skim."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.secret_sauce_cdl import _primary, merge_cdl_into_rows
from trendalgo.backtest.secret_sauce_lab import cross_features
from trendalgo.backtest.secret_sauce_lab.fat_beat import fat_beat_peer
from trendalgo.backtest.secret_sauce_lab.peer_refine import (
    _peer_skim_fallback,
    refine_lab_from_peers,
)
from trendalgo.backtest.secret_sauce_lab.peer_trade_bars import (
    _indexes_from_times,
    _lookup,
    pattern_and_inspire_seeds,
    peer_trade_indexes,
    rsx_seed_from_peer,
    top_peer_row,
)
from trendalgo.backtest.secret_sauce_structure import _ema, merge_structure_into_rows
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def test_cross_features_reexports() -> None:
    assert "rsi_xup_30" in cross_features.CROSS_KEYS or len(cross_features.CROSS_KEYS) > 0
    assert callable(cross_features.cross_up)
    assert callable(cross_features.merge_cross_into_rows)


def test_cdl_empty_and_primary_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    merge_cdl_into_rows(pd.DataFrame(), [])
    assert _primary({}) is None
    assert _primary({"other": np.array([1.0, 0.0])}) is not None

    df = pd.DataFrame(
        {
            "open": [1.0, 2.0],
            "high": [1.1, 2.1],
            "low": [0.9, 1.9],
            "close": [1.0, 2.0],
            "volume": [1.0, 1.0],
        }
    )
    rows = [{}, {}]

    def _bad_len(name: str, _df: pd.DataFrame, **_k: object) -> dict[str, np.ndarray]:
        return {"integer": np.array([1.0])}  # length mismatch → skip

    monkeypatch.setattr("trendalgo.ta.engine.compute", _bad_len)
    merge_cdl_into_rows(df, rows)
    assert all("cdl_cdldojistar" not in r for r in rows)


def test_structure_flat_and_empty() -> None:
    merge_structure_into_rows(np.array([]), np.array([]), np.array([]), [])
    closes = np.array([10.0, 10.0, 10.0, 10.0])
    highs = closes.copy()
    lows = closes.copy()
    rows = [{} for _ in closes]
    merge_structure_into_rows(closes, highs, lows, rows)
    assert rows[2]["fib_dist_382"] == 0.0
    assert rows[2]["swing_up_span"] == 0.0
    assert len(_ema(np.array([]), 5)) == 0


def test_top_peer_and_rsx_seed() -> None:
    rows = [
        {"indicator": "Oracle max", "net_pct": 999.0},
        {"indicator": "B&H", "net_pct": 10.0},
        {
            "indicator": "RSX",
            "net_pct": 40.0,
            "params": {
                "kind": "bounded_reversal",
                "entry_level": 25,
                "exit_level": 75,
                "length": 14,
            },
        },
        {"indicator": "RSI", "net_pct": 20.0, "params": {"kind": "bounded_reversal"}},
    ]
    top = top_peer_row(rows)
    assert top is not None and top["indicator"] == "RSX"
    seed = rsx_seed_from_peer(top)
    assert seed is not None
    assert seed["entry_level"] == 25.0
    assert rsx_seed_from_peer(None) is None


def test_peer_trade_indexes_empty_and_from_times() -> None:
    assert peer_trade_indexes(pd.DataFrame(), {"indicator": "RSI"}, fee=_fee(), stake=100) == (
        [],
        [],
    )
    idx = pd.date_range("2024-01-01", periods=5, freq="h")
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=idx)
    e, x = _indexes_from_times(
        df,
        [
            {"entry_index": 1, "exit_index": 3},
            {"entry_index": 99, "exit_index": -1},
        ],
    )
    assert e == [1] and x == [3]
    e2, x2 = _indexes_from_times(
        df,
        [{"entry_time": idx[0], "exit_time": idx[2]}],
    )
    assert e2 == [0] and x2 == [2]
    assert _lookup(idx, None) is None
    assert _lookup(idx, "not-a-stamp") is None


def test_pattern_and_inspire_seeds_fat_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    df = pd.DataFrame(
        {
            "open": [1.0] * 30,
            "high": [1.1] * 30,
            "low": [0.9] * 30,
            "close": [1.0] * 30,
            "volume": [1.0] * 30,
        }
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_trade_bars.peer_trade_indexes",
        lambda *_a, **_k: ([], []),
    )
    seeds = pattern_and_inspire_seeds(df, "1h", [], None, _fee(), 100.0)
    assert seeds
    assert all(s[2] == "peer_fat" for s in seeds)


def test_fat_beat_peer_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = MagicMock()
    regime = MagicMock()
    regime.direction = "long"
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.fat_beat.detect_regime",
        lambda _f: regime,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.fat_beat.bh_net_profit",
        lambda *_a, **_k: 0.0,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.fat_beat.seeds_for_weights",
        lambda *_a, **_k: [(MagicMock(), MagicMock(), "momentum")],
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.fat_beat.dossier_from_dict",
        lambda _d: None,
    )
    er, xr = MagicMock(), MagicMock()
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.fat_beat.search_best_pair",
        lambda *_a, **_k: (er, xr, 50.0, "peer_fat"),
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.fat_beat.is_exact_peer_clone",
        lambda *_a, **_k: False,
    )
    out: list[Any] = []
    fat_beat_peer({"heartbeat_dossier": None}, frame, "1h", [], 10.0, _fee(), 100.0, out)
    assert len(out) == 1
    assert out[0][2] == 50.0


def test_peer_skim_fallback_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = MagicMock()
    regime = MagicMock()
    regime.direction = "long"
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.bh_net_profit",
        lambda *_a, **_k: 0.0,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.detect_regime",
        lambda _f: regime,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.pattern_and_inspire_seeds",
        lambda *_a, **_k: [(MagicMock(), MagicMock(), "peer_pattern")],
    )
    er, xr = MagicMock(), MagicMock()
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.search_best_pair",
        lambda *_a, **_k: (er, xr, 20.0, "peer_pattern"),
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.is_exact_peer_clone",
        lambda *_a, **_k: False,
    )
    out: list[Any] = []
    _peer_skim_fallback({}, frame, "1h", [], None, 5.0, _fee(), 100.0, out)
    assert len(out) == 1


def test_refine_triggers_last_resort(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Oracle-first yields nothing under peer, RSX clear + fat + skim run."""
    df = pd.DataFrame(
        {
            "open": np.linspace(10, 20, 40),
            "high": np.linspace(10.5, 20.5, 40),
            "low": np.linspace(9.5, 19.5, 40),
            "close": np.linspace(10, 20, 40),
            "volume": np.full(40, 5.0),
        }
    )
    calls: list[str] = []

    def _oracle(*_a: Any, **_k: Any) -> None:
        calls.append("oracle")

    def _rsx(*_a: Any, **_k: Any) -> None:
        calls.append("rsx")

    def _fat(*_a: Any, **_k: Any) -> None:
        calls.append("fat")

    def _skim(*_a: Any, **_k: Any) -> None:
        calls.append("skim")
        out = _a[-1]
        out.append((MagicMock(), MagicMock(), 100.0, "skim", "4h", df, MagicMock()))

    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine._search_tf_oracle_first",
        _oracle,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine._rsx_clear_fallback",
        _rsx,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.fat_beat_peer",
        _fat,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine._peer_skim_fallback",
        _skim,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.pack_refine_candidate",
        lambda cand, *_a, **_k: (MagicMock(), MagicMock(), {"net_profit": cand[2]}, "4h"),
    )
    monkeypatch.setattr(
        "trendalgo.backtest.secret_sauce_lab.peer_refine.rsx_seed_from_peer",
        lambda _p: {
            "indicator": "RSX",
            "entry_level": 25,
            "exit_level": 70,
            "period": 14,
            "kind": "bounded_reversal",
        },
    )
    rows = [
        {
            "indicator": "RSX",
            "timeframe": "4h",
            "net_pct": 50.0,
            "params": {
                "kind": "bounded_reversal",
                "entry_level": 25,
                "exit_level": 70,
                "timeperiod": 14,
            },
        }
    ]
    sauce = {"indicator": "Secret Sauce", "timeframe": "1h", "net_profit": 1.0}
    hit = refine_lab_from_peers(
        sauce,
        rows,
        df,
        stake=1000.0,
        fee=_fee(),
        time_budget_s=1.0,
        frames_by_tf={"1h": df, "4h": df},
    )
    assert "oracle" in calls
    assert "rsx" in calls
    assert "fat" in calls
    assert "skim" in calls
    assert hit is not None
