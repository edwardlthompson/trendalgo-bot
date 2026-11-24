"""AV-G-ALR1 — notify surface includes Alerts ribbon masters + preview."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_more import load_notify_surface


def test_notify_surface_ribbon_keys(tmp_path: Path) -> None:
    data = load_notify_surface(tmp_path)
    assert data["ribbon_help"]
    assert len(data["ribbon"]) == 3
    ids = {r["id"] for r in data["ribbon"]}
    assert ids == {"entered", "left", "trades"}
    for row in data["ribbon"]:
        assert row["state"] in {"On", "Off"}
        assert row["windows_title"]
        assert row["telegram_body"]
    assert any(k["id"] == "entered" for k in data["kinds"])
