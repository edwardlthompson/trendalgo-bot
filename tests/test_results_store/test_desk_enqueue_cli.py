"""CLI --enqueue for Avalonia strip (AV-G1)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.__main__ import main
from trendalgo.results_store.desk_commands import peek_pending


def test_cli_enqueue_run_scan(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path), "--enqueue", "run_scan", "--lane", "crypto"]) == 0
    pending = peek_pending(tmp_path)
    assert pending is not None
    assert pending["action"] == "run_scan"
    assert pending["lane"] == "crypto"


def test_cli_desk_once_dry(tmp_path: Path) -> None:
    import json

    (tmp_path / "lts_scan_rows.json").write_text(
        json.dumps({"rows": [{"pair": "BTC/USD", "gain": 1.0}]}),
        encoding="utf-8",
    )
    assert main(["--root", str(tmp_path), "--enqueue", "run_scan"]) == 0
    assert main(["--root", str(tmp_path), "--desk-once", "--desk-dry"]) == 0
    assert peek_pending(tmp_path) is None
