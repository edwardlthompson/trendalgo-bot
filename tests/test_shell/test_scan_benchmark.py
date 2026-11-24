"""Tests for real-data benchmark helpers, lane fee schedules, and Secret Sauce budget guards."""

from __future__ import annotations

import json
import math
from pathlib import Path

from trendalgo.backtest.secret_sauce_lab.refine_ladder import refine_tf_budgets
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange
from trendalgo.results_store import scan_benchmark as sb


def test_fee_for_exchange_tradfi_and_forex_lane_defaults() -> None:
    tradfi = fee_for_exchange("tradfi", 52.0)
    forex = fee_for_exchange("forex", 52.0)
    unknown = fee_for_exchange("no-such-venue", 52.0)
    assert tradfi.source == "lane_default"
    assert tradfi.taker_pct < 0.001
    assert forex.source == "lane_default"
    assert forex.taker_pct < 0.001
    assert unknown.source == "bps"


def test_refine_tf_budgets_handles_infinite_budget_without_nan() -> None:
    budgets = refine_tf_budgets(4, float("inf"))
    assert len(budgets) == 4
    assert all(math.isinf(b) and b > 0 for b in budgets)


def test_write_progress_swallows_permission_error(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "benchmark_progress.json"

    def _deny(*_args, **_kwargs) -> None:
        raise PermissionError("locked by reader")

    monkeypatch.setattr(Path, "replace", _deny)
    sb._write_progress(target, {"running": True, "tests_done": 1})


def test_run_quick_benchmark_records_bars_subtests_and_results(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "scan_timing_last.json").write_text(
        json.dumps({"top_units": [{"strategy": "RSI", "timeframe": "1h", "elapsed_s": 0.42}]}),
        encoding="utf-8",
    )

    def _fake_scan(**kwargs):
        eid = kwargs["exchange_id"]
        on_prog = kwargs.get("on_progress")
        if on_prog is not None:
            on_prog({"done": 5, "phase": "catalog", "message": "Catalog TA", "bars_base": 720})
        rows = [
            {"indicator": "B&H", "timeframe": "1h", "net_pct": 1.5, "trades": 1},
            {"indicator": "RSI", "timeframe": "1h", "net_pct": 4.2, "trades": 6},
            {"indicator": "Secret Sauce Lab", "timeframe": "1h", "net_pct": 6.1, "trades": 5},
        ]
        ctx = {
            "data_source": f"1h:test:{eid}",
            "bars_base": 720,
            "n_frames": 3,
            "phase_s": {
                "load_s": 0.1,
                "pass1_s": 0.2,
                "deepen_s": 0.05,
                "mc_s": 0.01,
                "sauce_s": 0.3,
            },
        }
        return rows, ctx

    monkeypatch.setattr(sb, "scan_pair_strategies", _fake_scan)
    report = sb.run_quick_benchmark(tmp_path)

    assert report["ok"] is True
    assert len(report["assets"]) == 3
    assert all(a["bars"] == 720 for a in report["assets"])
    assert any(s["component"] == "Outcome: Secret Sauce Lab" for s in report["subtests"])
    assert any(s["component"] == "Slow unit: RSI" for s in report["subtests"])
    assert (tmp_path / sb.RESULTS_FILE).exists()
    prog = json.loads((tmp_path / sb.PROGRESS_FILE).read_text(encoding="utf-8"))
    assert prog["running"] is False
    assert prog["phase"] == "done"


def test_sidecar_ping_and_surface(tmp_path: Path, monkeypatch) -> None:
    from trendalgo.results_store import sidecar

    monkeypatch.setattr(
        sidecar,
        "export_surface",
        lambda _r, s, lane="crypto", pair="": {"s": s, "l": lane, "p": pair},
    )
    ping = sidecar.handle_request(tmp_path, {"id": 1, "op": "ping"})
    assert ping == {"id": 1, "ok": True, "data": {"pong": True}}
    surf = sidecar.handle_request(
        tmp_path,
        {"id": 2, "op": "surface", "surface": "results", "lane": "forex", "pair": "EUR/USD"},
    )
    assert surf == {"id": 2, "ok": True, "data": {"s": "results", "l": "forex", "p": "EUR/USD"}}


def test_multi_desk_scan_dry_run_all_lanes(tmp_path: Path) -> None:
    from trendalgo.results_store.multi_desk_scan import run_all_desks_parallel

    out = run_all_desks_parallel(
        tmp_path,
        "cid-1",
        "run_all_scans",
        dry_run=True,
        run_live=lambda _r, ln, _f: {"lane": ln, "rows": 0},
        publish=lambda *_a, **_k: ("done", 0),
    )
    assert out["status"] == "done"
    assert set(out["lanes"].keys()) == {"crypto", "tradfi", "forex"}
