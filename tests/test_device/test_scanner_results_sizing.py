"""Results dialog sizing: fit columns, scroll as needed, no maxHeight cap."""

from __future__ import annotations

from pathlib import Path


def test_results_dialog_source_has_no_max_height_cap() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "trendalgo"
        / "device"
        / "views"
        / "scanner_results.py"
    )
    source = path.read_text(encoding="utf-8")
    # Only assert the show_results_dialog body — AdjustToContents, no height cap.
    start = source.index("def show_results_dialog")
    end = source.index("\ndef ", start + 1)
    body = source[start:end]
    assert "setMaximumHeight" not in body
    assert "AdjustToContents" in body
    assert "ScrollBarAsNeeded" in body
    assert "fit_table_columns" in body or "populate_results_table" in body
    assert "WindowMinMaxButtonsHint" in body
    assert "results_dialog_width" in body or "load_results_prefs" in body
    assert "showMaximized" in body
    assert "finished.connect" in body
    assert "BacktestColumnFilterRow" in body
    assert "filter_rows" in body
