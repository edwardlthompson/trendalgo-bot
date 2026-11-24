"""AV-G-OTH1 — export hub journal/plan/scan."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.export_model import PLAN_JSON_NAME
from trendalgo.device.profile import PLAN_FILE
from trendalgo.results_store.desk_export_hub import load_export_hub_surface, run_export_hub


def test_export_hub_surface(tmp_path: Path) -> None:
    data = load_export_hub_surface(tmp_path)
    assert data["ok"] is True
    assert data["title"]
    assert {a["id"] for a in data["actions"]} == {"journal", "plan", "scan"}
    assert Path(data["folder"]).is_dir()


def test_export_hub_plan_json(tmp_path: Path) -> None:
    plan = tmp_path / PLAN_FILE
    plan.write_text(json.dumps({"version": 1, "bots": []}), encoding="utf-8")
    dest = tmp_path / "out"
    result = run_export_hub(tmp_path, {"kind": "plan", "dest": str(dest)})
    assert result["ok"] is True
    assert result["name"] == PLAN_JSON_NAME
    assert (dest / PLAN_JSON_NAME).is_file()


def test_export_hub_missing_journal(tmp_path: Path) -> None:
    result = run_export_hub(tmp_path, {"kind": "journal", "dest": str(tmp_path / "out")})
    assert result["ok"] is False
    assert result["error"] == "missing"
    assert result["problems"]
