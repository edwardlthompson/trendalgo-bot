"""Sauce Pan prefs, eligibility, and manual Sauce-only job."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from trendalgo.device.opportunity_sauce import OPPORTUNITY_SAUCE_TOP_N
from trendalgo.device.scan_bt_prefs import (
    SAUCE_TOP_N_MAX,
    ScanBtPrefs,
    clamp_sauce_top_n,
    load_scan_bt_prefs,
    save_scan_bt_prefs,
)


def test_clamp_sauce_top_n() -> None:
    assert clamp_sauce_top_n(0) == 1
    assert clamp_sauce_top_n(-3) == 1
    assert clamp_sauce_top_n(3) == 3
    assert clamp_sauce_top_n(999) == SAUCE_TOP_N_MAX
    assert clamp_sauce_top_n("nope") == OPPORTUNITY_SAUCE_TOP_N


def test_scan_bt_prefs_sauce_pan_round_trip(tmp_path: Path) -> None:
    prefs = ScanBtPrefs(
        timeframes=["1h"],
        strategy_denylist=[],
        sauce_with_scan=False,
        sauce_top_n=4,
        market_context_with_scan=False,
    )
    save_scan_bt_prefs(tmp_path, prefs)
    loaded = load_scan_bt_prefs(tmp_path)
    assert loaded.sauce_with_scan is False
    assert loaded.sauce_top_n == 4
    assert loaded.market_context_with_scan is False


def test_scan_bt_prefs_sauce_defaults_when_missing(tmp_path: Path) -> None:
    import json

    path = tmp_path / "scan_bt_prefs.json"
    path.write_text(
        json.dumps(
            {
                "timeframes": ["1h"],
                "strategy_denylist": [],
                "bt_signal_set": "all_ta",
            }
        ),
        encoding="utf-8",
    )
    loaded = load_scan_bt_prefs(tmp_path)
    assert loaded.sauce_with_scan is True
    assert loaded.sauce_top_n == OPPORTUNITY_SAUCE_TOP_N
    assert loaded.market_context_with_scan is True


def test_coins_eligible_for_sauce() -> None:
    from trendalgo.device.opportunity_sauce_job import coins_eligible_for_sauce

    filtered = [
        {"symbol": "A", "backtest_top_strategies": [{"indicator": "RSI", "net_pct": 1}]},
        {"symbol": "B", "backtest_top_strategies": []},
        {"symbol": "C"},
        {"symbol": "D", "backtest_top_strategies": [{"indicator": "EMA", "net_pct": 2}]},
    ]
    elig = coins_eligible_for_sauce(filtered)
    assert [c["symbol"] for c in elig] == ["A", "D"]


def _stub_progress_reporter(monkeypatch: pytest.MonkeyPatch, job: Any) -> MagicMock:
    """Avoid background ProgressReporter threads in unit tests."""
    reporter = MagicMock()
    monkeypatch.setattr(job, "ProgressReporter", lambda _root: reporter)
    return reporter


def test_manual_sauce_pan_never_runs_catalog(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trendalgo.device import opportunity_sauce_job as job
    from trendalgo.device.scan_bt_prefs import ScanBtPrefs, save_scan_bt_prefs

    reporter = _stub_progress_reporter(monkeypatch, job)
    save_scan_bt_prefs(
        tmp_path,
        ScanBtPrefs(timeframes=["1h"], sauce_with_scan=False, sauce_top_n=2),
    )
    filtered = [
        {
            "symbol": "HIGH",
            "backtest_top_strategies": [
                {"indicator": "Oracle max", "net_pct": 30.0, "symbol": "HIGH"}
            ],
        },
        {
            "symbol": "MID",
            "backtest_top_strategies": [
                {"indicator": "Oracle max", "net_pct": 10.0, "symbol": "MID"}
            ],
        },
        {
            "symbol": "LOW",
            "backtest_top_strategies": [
                {"indicator": "Oracle max", "net_pct": 1.0, "symbol": "LOW"}
            ],
        },
    ]
    catalog_calls: list[bool] = []

    def fake_sauce_pass(
        coins: list[dict[str, Any]],
        *,
        prefs_root: Path,
        seed_rows_by_symbol: dict[str, list[dict[str, Any]]],
        top_n: int | None = None,
    ) -> dict[str, Any]:
        assert prefs_root == tmp_path
        assert top_n == 2
        assert [c["symbol"] for c in coins] == ["HIGH", "MID"]
        assert set(seed_rows_by_symbol) >= {"HIGH", "MID"}
        # Sauce-only: no catalog flag exists on this API.
        catalog_calls.append(False)
        return {
            "results": [
                {"symbol": "HIGH", "indicator": "Secret Sauce Lab", "net_pct": 40.0},
                {"symbol": "MID", "indicator": "Secret Sauce Lab", "net_pct": 12.0},
            ],
            "sauce_symbols": ["HIGH", "MID"],
            "market_contexts": {},
        }

    import trendalgo.device.scanner_all_ta_bt as bt_mod

    monkeypatch.setattr(bt_mod, "run_opportunity_sauce_pass", fake_sauce_pass)

    board = list(filtered) + [{"symbol": "OTHER", "backtest_top_strategies": [{"net_pct": 0}]}]
    monkeypatch.setattr(job, "load_lts_rows", lambda _r, **_k: list(board))
    saved: list[list[dict[str, Any]]] = []
    monkeypatch.setattr(job, "save_lts_rows", lambda _r, rows, **_k: saved.append(list(rows)))
    monkeypatch.setattr(
        "trendalgo.lts_vendor.bridge.merge_backtest_into_coins",
        lambda coins, summary: [
            {
                **c,
                "backtest_top_strategies": [
                    r for r in summary.get("results", []) if str(r.get("symbol")) == c["symbol"]
                ],
            }
            for c in coins
        ],
    )
    monkeypatch.setattr(job, "get_scan_progress", lambda: MagicMock())

    out = job.run_manual_sauce_pan(tmp_path, filtered)
    assert out["ok"] is True
    assert out["sauce_symbols"] == ["HIGH", "MID"]
    assert catalog_calls == [False]
    assert saved
    by_sym = {str(c["symbol"]): c for c in saved[0]}
    assert by_sym["HIGH"]["backtest_top_strategies"]
    assert by_sym["OTHER"]["backtest_top_strategies"] == [{"net_pct": 0}]
    reporter.start.assert_called_once()
    reporter.stop.assert_called_once()


def test_manual_sauce_pan_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device import opportunity_sauce_job as job

    reporter = _stub_progress_reporter(monkeypatch, job)
    progress = MagicMock()
    monkeypatch.setattr(job, "get_scan_progress", lambda: progress)
    out = job.run_manual_sauce_pan(tmp_path, [{"symbol": "X"}])
    assert out["ok"] is False
    assert out["sauce_symbols"] == []
    progress.begin_job.assert_called_once_with(job.SAUCE_PAN_LABEL)
    reporter.start.assert_called_once()
    reporter.stop.assert_called_once()


def test_manual_sauce_pan_starts_progress_reporter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from trendalgo.device import opportunity_sauce_job as job
    from trendalgo.device.scan_bt_prefs import ScanBtPrefs, save_scan_bt_prefs

    reporter = _stub_progress_reporter(monkeypatch, job)
    progress = MagicMock()
    monkeypatch.setattr(job, "get_scan_progress", lambda: progress)
    save_scan_bt_prefs(tmp_path, ScanBtPrefs(timeframes=["1h"], sauce_top_n=1))
    monkeypatch.setattr(
        "trendalgo.device.scanner_all_ta_bt.run_opportunity_sauce_pass",
        lambda *_a, **_k: {
            "results": [],
            "sauce_symbols": ["A"],
            "market_contexts": {},
        },
    )
    monkeypatch.setattr(job, "load_lts_rows", lambda _r, **_k: [])
    monkeypatch.setattr(job, "save_lts_rows", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "trendalgo.lts_vendor.bridge.merge_backtest_into_coins",
        lambda coins, _summary: list(coins),
    )
    filtered = [
        {
            "symbol": "A",
            "backtest_top_strategies": [{"indicator": "RSI", "net_pct": 5.0}],
        }
    ]
    out = job.run_manual_sauce_pan(tmp_path, filtered)
    assert out["ok"] is True
    progress.begin_job.assert_called_once_with(job.SAUCE_PAN_LABEL)
    reporter.start.assert_called_once()
    reporter.stop.assert_called_once()
