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
    assert not bar.auto_scan.isVisibleTo(bar)  # desk auto-scan lives on Settings ETA
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


def test_settings_dialog_has_no_show_lane_checkboxes(tmp_path: Path, qtbot: QtBot) -> None:
    dlg = ScanBacktestSettingsDialog(tmp_path)
    qtbot.addWidget(dlg)
    from PySide6.QtWidgets import QCheckBox

    labels = {box.text() for box in dlg.findChildren(QCheckBox)}
    assert not any(t.startswith("Show ") for t in labels)
    assert "Show crypto" not in labels
    assert "Show TradFi" not in labels
    assert "Show Forex" not in labels


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
    assert dlg._continuous.isChecked()
    dlg._every.setValue(90)
    dlg._heatmap.setChecked(False)
    dlg._vol.setValue(250_000)
    dlg._continuous.setChecked(False)
    dlg._save()
    assert chrome.get("interval_minutes") == 90
    assert chrome.get("heatmap_enabled") is False
    assert chrome.get("min_volume_usd") == 250_000.0
    assert "min_uniformity" not in chrome
    assert chrome.get("require_continuous_1h") is False
    assert "scan_exchanges" in chrome


def test_filter_bar_status_includes_last_took(qtbot: QtBot) -> None:
    bar = ScannerFilterBar()
    qtbot.addWidget(bar)
    bar.set_last_elapsed_s(125)
    text = bar.status_text()
    assert "Last scan took" in text
    assert "2m" in text


def test_settings_dialog_two_column_wider(tmp_path: Path, qtbot: QtBot) -> None:
    dlg = ScanBacktestSettingsDialog(tmp_path)
    qtbot.addWidget(dlg)
    assert dlg.minimumWidth() >= 720


def test_settings_dialog_strategies_right_ohlcvt_left(tmp_path: Path, qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QScrollArea

    from trendalgo.device import strings as S
    from trendalgo.device.views.collapsible_section import CollapsibleSection

    dlg = ScanBacktestSettingsDialog(tmp_path)
    qtbot.addWidget(dlg)
    scroll = dlg.findChild(QScrollArea)
    assert scroll is not None
    host = scroll.widget()
    assert host is not None
    cols = host.layout()
    assert cols is not None and cols.count() == 3

    def _titles(lay: object) -> list[str]:
        out: list[str] = []
        for i in range(lay.count()):  # type: ignore[attr-defined]
            item = lay.itemAt(i)  # type: ignore[attr-defined]
            w = item.widget() if item is not None else None
            if isinstance(w, CollapsibleSection):
                out.append(w._title.text())  # noqa: SLF001
        return out

    col1 = cols.itemAt(0).layout()
    col2 = cols.itemAt(1).layout()
    col3 = cols.itemAt(2).layout()
    assert S.SCAN_BT_OHLCVT_SECTION in _titles(col1)
    assert S.SCAN_BT_EXTRAS_SECTION in _titles(col1)
    assert S.SCAN_BT_TF_SECTION in _titles(col2)
    assert S.SCAN_BT_TA_SECTION not in _titles(col2)
    assert S.SCAN_BT_TA_SECTION in _titles(col3)


def test_settings_dialog_forex_hides_crypto_primary(tmp_path: Path, qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QScrollArea

    from trendalgo.device import strings as S
    from trendalgo.device.views.collapsible_section import CollapsibleSection

    dlg = ScanBacktestSettingsDialog(tmp_path, lane="forex")
    qtbot.addWidget(dlg)
    scroll = dlg.findChild(QScrollArea)
    assert scroll is not None
    col1 = scroll.widget().layout().itemAt(0).layout()
    titles: list[str] = []
    for i in range(col1.count()):
        w = col1.itemAt(i).widget()
        if isinstance(w, CollapsibleSection):
            titles.append(w._title.text())  # noqa: SLF001
    assert S.SCAN_BT_PRIMARY_SECTION not in titles
    assert S.SCAN_BT_OHLCVT_SECTION not in titles
    assert S.LANE_FILTER_SECTION not in titles  # Forex has no ADV/max filters
    assert not dlg._exchange.isVisibleTo(dlg)


def test_settings_dialog_tradfi_has_adv_no_max(tmp_path: Path, qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QLabel, QScrollArea

    from trendalgo.device import strings as S
    from trendalgo.device.views.collapsible_section import CollapsibleSection

    dlg = ScanBacktestSettingsDialog(tmp_path, lane="tradfi")
    qtbot.addWidget(dlg)
    assert dlg._lane_adv is not None
    assert dlg._lane_price is not None
    assert not hasattr(dlg, "_lane_max")
    scroll = dlg.findChild(QScrollArea)
    assert scroll is not None
    col1 = scroll.widget().layout().itemAt(0).layout()
    titles: list[str] = []
    for i in range(col1.count()):
        w = col1.itemAt(i).widget()
        if isinstance(w, CollapsibleSection):
            titles.append(w._title.text())  # noqa: SLF001
    assert S.LANE_FILTER_SECTION in titles
    labels = " ".join(lab.text() for lab in dlg.findChildren(QLabel))
    assert "Max symbols" not in labels
    assert "Max pairs" not in labels


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
