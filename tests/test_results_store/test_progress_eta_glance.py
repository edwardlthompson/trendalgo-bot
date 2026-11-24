"""AV-G-STR9 — progress surface includes ETA + pair glance fields."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.profile import write_json
from trendalgo.device.scan_progress import progress_file_name
from trendalgo.results_store.desk_progress import load_progress_surface


def test_progress_surface_eta_and_pair(tmp_path: Path) -> None:
    write_json(
        tmp_path / progress_file_name("crypto"),
        {
            "phase": "Scanning",
            "busy": True,
            "done": 3,
            "total": 10,
            "current_pair": "eth",
            "pairs_done": 3,
            "pairs_total": 10,
            "elapsed_s": 30,
            "prior_s": 100,
            "events": [{"message": "tick"}],
        },
    )
    payload = load_progress_surface(tmp_path, lane="crypto")
    assert payload["current_pair"] == "ETH/USD"
    assert payload["percent"] == 30.0
    assert "eta_label" in payload
    assert "3/10" in payload["pairs_label"]


def test_progress_header_prefers_state_phase_over_error_message(tmp_path: Path) -> None:
    write_json(
        tmp_path / progress_file_name("crypto"),
        {
            "message": "All-TA coin failed: ",
            "state": {
                "phase": "Backtest (All TA catalog)…",
                "active": True,
                "status": "running",
                "step_done": 9,
                "step_total": 160,
                "current_pair": "INFI/USD",
                "pairs_done": 9,
                "pairs_total": 160,
            },
            "events": [{"message": "All-TA coin failed: "}],
        },
    )
    payload = load_progress_surface(tmp_path, lane="crypto")
    assert payload["phase"].startswith("Backtest")
    assert "failed" not in payload["phase"].lower()
    assert payload["current_pair"] == "INFI/USD"
    assert payload["busy"] is True
