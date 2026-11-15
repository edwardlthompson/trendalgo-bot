"""Scanner chrome: action buttons + Settings board filters + status dialog."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QPushButton
from pytestqt.qtbot import QtBot

from trendalgo.device.views.dex_watch_panel import DexWatchDialog
from trendalgo.device.views.scan_bt_settings_dialog import ScanBacktestSettingsDialog
from trendalgo.device.views.scanner_filters import ScannerFilterBar, show_scan_status_dialog


def test_filter_bar_shows_action_buttons_not_board_filters(qtbot: QtBot) -> None:
    bar = ScannerFilterBar()
    qtbot.addWidget(bar)
    bar.show()
    assert isinstance(bar.settings, QPushButton)
    assert bar.sauce_pan.isVisibleTo(bar)
    assert bar.pool_watch.isVisibleTo(bar)
    assert bar.refresh_prices.isVisibleTo(bar)
    assert bar.share.isVisibleTo(bar)
    assert bar.status_btn.isVisibleTo(bar)
    assert not bar.exchange.isVisible()
    assert not bar.vol.isVisible()
    assert not bar.every.isVisible()
    assert not bar.heatmap.isVisible()
    bar.every.setValue(90)
    bar.set_eta_text("Est. ~10s")
    bar.set_auto_status_text("Next auto-scan in 5 min.")
    text = bar.status_text()
    assert "every 90 min" in text
    assert "Est. ~10s" in text
    assert "Next auto-scan" in text


def test_filter_bar_prefs_round_trip(qtbot: QtBot) -> None:
    bar = ScannerFilterBar()
    qtbot.addWidget(bar)
    bar.load(
        {
            "min_volume_usd": 1_000_000,
            "interval_minutes": 120,
            "heatmap_enabled": True,
            "scan_exchanges": [],
        }
    )
    dumped = bar.dump()
    assert dumped["interval_minutes"] == 120
    assert dumped["heatmap_enabled"] is True
    assert dumped["min_volume_usd"] == 1_000_000.0


def test_settings_dialog_chrome_board_filters(tmp_path: Path, qtbot: QtBot) -> None:
    chrome: dict = {}
    dlg = ScanBacktestSettingsDialog(
        tmp_path,
        interval_minutes=75,
        heatmap_enabled=True,
        min_volume_usd=500_000,
        scan_exchanges=[],
        exchange_options=[("kraken", "Kraken")],
        chrome_out=chrome,
    )
    qtbot.addWidget(dlg)
    assert dlg._every.value() == 75
    assert dlg._heatmap.isChecked()
    assert dlg._vol.value() == 500_000
    dlg._every.setValue(90)
    dlg._heatmap.setChecked(False)
    dlg._vol.setValue(250_000)
    dlg._save()
    assert chrome.get("interval_minutes") == 90
    assert chrome.get("heatmap_enabled") is False
    assert chrome.get("min_volume_usd") == 250_000.0
    assert "scan_exchanges" in chrome


def test_settings_dialog_two_column_wider(tmp_path: Path, qtbot: QtBot) -> None:
    dlg = ScanBacktestSettingsDialog(tmp_path)
    qtbot.addWidget(dlg)
    assert dlg.minimumWidth() >= 720


def test_settings_dialog_results_view_out(tmp_path: Path, qtbot: QtBot) -> None:
    results: dict = {}
    dlg = ScanBacktestSettingsDialog(
        tmp_path,
        results_heatmap=True,
        results_perfect=False,
        results_out=results,
    )
    qtbot.addWidget(dlg)
    assert dlg._results_heatmap is not None
    assert dlg._results_heatmap.isChecked()
    assert dlg._results_perfect is not None
    dlg._results_perfect.setChecked(True)
    dlg._save()
    assert results.get("heatmap_enabled") is True
    assert results.get("perfect_only") is True


def test_dex_watch_dialog_runs_job(
    tmp_path: Path, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []

    def fake_job(root: Path) -> dict:
        calls.append(root)
        return {"rows": 2, "venues": ["ethereum", "base"]}

    monkeypatch.setattr(
        "trendalgo.device.views.dex_watch_panel.dex_watch_scan_job",
        fake_job,
    )
    dlg = DexWatchDialog(tmp_path)
    qtbot.addWidget(dlg)
    dlg._start()
    assert calls == [tmp_path]
    assert dlg.result_payload() is not None


def test_show_scan_status_dialog(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "PySide6.QtWidgets.QDialog.exec",
        lambda self: 1,
    )
    show_scan_status_dialog("every 60 min · Next auto-scan in 11 min.")
