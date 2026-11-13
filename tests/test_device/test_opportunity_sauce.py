"""Opportunity Sauce top-N by Oracle ranking."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from trendalgo.device.opportunity_sauce import (
    OPPORTUNITY_SAUCE_TOP_N,
    load_sauce_ever,
    mark_sauce_ever,
    oracle_rank_score,
    select_sauce_symbols,
    select_sauce_symbols_with_first_join,
)


def test_oracle_rank_prefers_oracle_max() -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 50.0},
        {"indicator": "Oracle max", "net_pct": 12.0},
        {"indicator": "B&H", "net_pct": 99.0},
    ]
    assert oracle_rank_score(rows) == 12.0


def test_oracle_rank_falls_back_to_best_catalog() -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 5.0},
        {"indicator": "MACD", "net_pct": 11.0},
        {"indicator": "B&H", "net_pct": 99.0},
        {"indicator": "Secret Sauce Lab", "net_pct": 80.0},
    ]
    assert oracle_rank_score(rows) == 11.0


def test_select_sauce_symbols_top_n_and_order() -> None:
    scored = [("ZZZ", 1.0), ("AAA", 9.0), ("MMM", 5.0), ("BBB", 9.0)]
    assert select_sauce_symbols(scored, top_n=2) == ["AAA", "BBB"]
    assert OPPORTUNITY_SAUCE_TOP_N == 10
    assert len(select_sauce_symbols(scored, top_n=10)) == 4


def test_select_sauce_first_join_unions_newcomers() -> None:
    scored = [("HIGH", 30.0), ("MID", 10.0), ("LOW", 1.0)]
    # Top-2 only, but LOW never sauced → included once.
    got = select_sauce_symbols_with_first_join(scored, ever=set(), top_n=2)
    assert got[:2] == ["HIGH", "MID"]
    assert "LOW" in got
    # After ever marks LOW, future top-2 skips LOW.
    got2 = select_sauce_symbols_with_first_join(scored, ever={"LOW"}, top_n=2)
    assert got2 == ["HIGH", "MID"]


def test_sauce_ever_persist_roundtrip(tmp_path: Any) -> None:
    assert load_sauce_ever(tmp_path) == set()
    mark_sauce_ever(tmp_path, ["btc", "ETH"])
    assert load_sauce_ever(tmp_path) == {"BTC", "ETH"}
    mark_sauce_ever(tmp_path, ["SOL"])
    assert load_sauce_ever(tmp_path) == {"BTC", "ETH", "SOL"}


def test_include_sauce_false_skips_lab(monkeypatch: Any) -> None:
    import pandas as pd

    from trendalgo.device import pair_strategy_scan as scan

    idx = pd.date_range("2024-01-01", periods=80, freq="h", tz="UTC")
    close = pd.Series(range(100, 180), index=idx, dtype=float)
    frame = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0},
        index=idx,
    )
    mine = MagicMock(return_value={"indicator": "Secret Sauce Lab", "net_pct": 1.0})
    monkeypatch.setattr(scan, "mine_and_eval_secret_sauce", mine)
    monkeypatch.setattr(
        scan,
        "load_base_ohlcv_frame",
        lambda **_k: (frame, "1h", "test", 0.0),
    )
    monkeypatch.setattr(scan, "run_catalog_pass2", lambda **_k: ([], {}, 0, []))
    monkeypatch.setattr(scan, "deepen_seeds", lambda *_a, **_k: [])
    monkeypatch.setattr(scan, "stamp_rows_protective_tsl", lambda rows, *_a, **_k: rows)
    monkeypatch.setattr(scan, "buy_and_hold_row", lambda *_a, **_k: None)
    monkeypatch.setattr(
        scan,
        "oracle_max_row",
        lambda *_a, **_k: {
            "strategy_id": "ORACLE",
            "net_profit": 10.0,
            "trades": 1,
            "wins": 1,
        },
    )
    fee = MagicMock()
    rows, ctx = scan.scan_pair_strategies(
        symbol="PEPE",
        pair="PEPE/USD",
        timeframes=("1h",),
        strat_list=("RSI",),
        stake=1000.0,
        fee=fee,
        loader=MagicMock(),
        include_sauce=False,
    )
    mine.assert_not_called()
    assert ctx is not None
    assert ctx.get("include_sauce") is False
    assert not any(str(r.get("indicator") or "").startswith("Secret Sauce") for r in rows)


def test_sauce_only_rows_skips_catalog_and_deepen(monkeypatch: Any) -> None:
    import pandas as pd

    from trendalgo.device import pair_strategy_sauce_pass as sauce_mod
    from trendalgo.device import pair_strategy_scan as scan

    idx = pd.date_range("2024-01-01", periods=80, freq="h", tz="UTC")
    close = pd.Series(range(100, 180), index=idx, dtype=float)
    frame = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0},
        index=idx,
    )
    catalog = MagicMock(return_value=([], {}, 0, []))
    deepen = MagicMock(return_value=[])
    monkeypatch.setattr(scan, "run_catalog_pass2", catalog)
    monkeypatch.setattr(scan, "deepen_seeds", deepen)
    monkeypatch.setattr(
        sauce_mod,
        "load_base_ohlcv_frame",
        lambda **_k: (frame, "1h", "test", 0.0),
    )
    monkeypatch.setattr(sauce_mod, "mine_and_eval_secret_sauce", MagicMock(return_value=None))
    monkeypatch.setattr(sauce_mod, "coincidence_sauce_row", MagicMock(return_value=None))
    monkeypatch.setattr(sauce_mod, "stamp_rows_protective_tsl", lambda rows, *_a, **_k: rows)
    seed = [
        {
            "indicator": "Oracle max",
            "strategy_id": "ORACLE",
            "net_pct": 12.0,
            "timeframe": "1h",
            "net_profit": 10.0,
            "trades": 1,
            "wins": 1,
        }
    ]
    fee = MagicMock()
    rows, ctx = scan.scan_pair_strategies(
        symbol="PEPE",
        pair="PEPE/USD",
        timeframes=("1h",),
        strat_list=("RSI",),
        stake=1000.0,
        fee=fee,
        loader=MagicMock(),
        sauce_only_rows=seed,
    )
    catalog.assert_not_called()
    deepen.assert_not_called()
    assert ctx is not None
    assert ctx.get("sauce_only") is True
    assert any(str(r.get("indicator") or "").startswith("Oracle") for r in rows)
