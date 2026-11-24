"""Alerts history surface (AV-G8)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_export import load_alerts_surface


def test_alerts_surface_filters_tab(tmp_path: Path) -> None:
    (tmp_path / "scanner_alerts.json").write_text(
        json.dumps(
            {
                "alerts": [
                    {"kind": "scan_log", "reason": "done", "pair": "BTC/USD"},
                    {"kind": "qualified_enter", "reason": "enter", "pair": "ETH/USD"},
                ]
            }
        ),
        encoding="utf-8",
    )
    logs = load_alerts_surface(tmp_path, tab="logs")
    assert logs["count"] == 1
    entered = load_alerts_surface(tmp_path, tab="entered")
    assert entered["rows"][0]["pair"] == "ETH/USD"
