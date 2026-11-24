"""Bots hub plan.json surface (AV-G9)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_export import load_bots_surface


def test_bots_surface_reads_plan(tmp_path: Path) -> None:
    (tmp_path / "plan.json").write_text(
        json.dumps(
            {
                "plan_version": 1,
                "bots": [
                    {
                        "name": "Alpha",
                        "pair": "BTC/USD",
                        "timeframe": "1h",
                        "indicator": "RSI",
                        "stake_usd": 25,
                        "trailing_stop_pct": 2,
                        "stake_mode": "fixed_usd",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    data = load_bots_surface(tmp_path)
    assert data["count"] == 1
    assert data["rows"][0]["pair"] == "BTC/USD"
    assert data["host_badge"] == "local"
