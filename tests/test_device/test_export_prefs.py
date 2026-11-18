"""PNG export folder memory."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.export_prefs import (
    ExportPrefs,
    load_export_prefs,
    remember_export_dir,
    save_export_prefs,
    suggested_png_path,
)
from trendalgo.device.portfolio_share import default_portfolio_export_path
from trendalgo.device.scanner_share import default_scanner_export_path


def test_export_prefs_roundtrip(tmp_path: Path) -> None:
    custom = tmp_path / "shots"
    custom.mkdir()
    save_export_prefs(tmp_path, ExportPrefs(last_export_dir=str(custom)))
    loaded = load_export_prefs(tmp_path)
    assert loaded.last_export_dir == str(custom)
    suggested = suggested_png_path(tmp_path, "scanner-list.png")
    assert suggested.parent == custom.resolve() or suggested.parent == custom
    assert suggested.name == "scanner-list.png"


def test_suggested_falls_back_when_missing(tmp_path: Path) -> None:
    save_export_prefs(tmp_path, ExportPrefs(last_export_dir=str(tmp_path / "gone")))
    suggested = suggested_png_path(tmp_path, "x.png")
    assert suggested.parent == (tmp_path / "exports")
    assert suggested.name == "x.png"


def test_remember_export_dir_seeds_helpers(tmp_path: Path) -> None:
    custom = tmp_path / "my-exports"
    custom.mkdir()
    remember_export_dir(tmp_path, custom / "shot.png")
    port = default_portfolio_export_path(tmp_path, label="overview")
    scan = default_scanner_export_path(tmp_path, label="list")
    assert port.parent == custom.resolve() or port.parent == custom
    assert scan.parent == custom.resolve() or scan.parent == custom
    assert port.name.startswith("portfolio-")
    assert scan.name.startswith("scanner-")
