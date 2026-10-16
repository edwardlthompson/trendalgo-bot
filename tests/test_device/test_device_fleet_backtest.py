"""Fleet backtest device slice: model, progress file, job stub, and fleet panel (offline)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.fleet_backtest_job import fleet_backtest_job  # noqa: E402
from trendalgo.device.fleet_backtest_model import (  # noqa: E402
    plan_prefill_from_row,
    progress_line,
    top10_table_rows,
    validate_fleet_backtest,
)
from trendalgo.device.fleet_backtest_offline import OFFLINE_RESULT  # noqa: E402
from trendalgo.device.fleet_progress import clear_progress, read_progress  # noqa: E402
from trendalgo.device.views.fleet_backtest_panel import FleetBacktestPanel  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402

RUN_TIMEOUT_MS = 60_000


def test_validate_fleet_backtest_accepts_btc_usd() -> None:
    req, problems = validate_fleet_backtest(exchange_id="kraken", pair="BTC/USD", stake="1000")
    assert problems == []
    assert req is not None
    assert req.pair == "BTC/USD"


def test_progress_line_includes_phase_count_and_eta() -> None:
    line = progress_line(
        {
            "status": "running",
            "phase": "pass1",
            "completed": 5,
            "total_combinations": 10,
            "progress_pct": 50,
            "eta_seconds": 90,
            "current_test": "MACD @ 60",
        }
    )
    assert "pass1" in line
    assert "5/10" in line
    assert "ETA" in line
    assert "MACD" in line


def test_top10_table_rows_show_delta_vs_buy_hold() -> None:
    rows = top10_table_rows(OFFLINE_RESULT["top10"], OFFLINE_RESULT["buy_and_hold"])
    assert rows[0][0] == "1"
    assert rows[0][5] == "+32.50"


def test_plan_prefill_maps_rsi_one_hour() -> None:
    fields, note = plan_prefill_from_row(
        OFFLINE_RESULT["top10"][0],
        pair="BTC/USD",
        stake_usd=1000.0,
    )
    assert note == ""
    assert fields is not None
    assert fields["indicator"] == "RSI"
    assert fields["timeframe"] == "1h"
    assert fields["stop"] == "5"


def test_offline_fleet_job_writes_progress_and_returns_top10(ctx: DeviceContext) -> None:
    clear_progress(ctx.root)
    result = fleet_backtest_job(
        ctx.root,
        ctx.root,
        "kraken",
        "BTC/USD",
        1000.0,
        _offline_payload=OFFLINE_RESULT,
    )
    assert len(result["top10"]) == 1
    snap = read_progress(ctx.root)
    assert snap is not None
    assert snap.get("status") == "complete"
    clear_progress(ctx.root)


def test_fleet_panel_runs_offline_job_and_shows_top10(
    qtbot: QtBot,
    ctx: DeviceContext,
    pool: WorkerPool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trendalgo.device.fleet_backtest_offline import offline_fleet_backtest_job
    from trendalgo.device.views import fleet_backtest_panel as panel_mod

    monkeypatch.setattr(panel_mod, "fleet_backtest_job", offline_fleet_backtest_job)
    fleet = FleetBacktestPanel(ctx, pool)
    qtbot.addWidget(fleet)
    fleet._pair.setText("BTC/USD")
    fleet._run.click()
    qtbot.waitUntil(lambda: fleet._status.text() == S.FLEET_BACKTEST_DONE, timeout=RUN_TIMEOUT_MS)
    assert fleet._results.rowCount() == 1
    assert "42.50" in fleet._results.item(0, 3).text()
