"""OHLCVT download button: progress bar + completion acknowledgement."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox, QProgressBar, QPushButton

pytest.importorskip("pytestqt")
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S
from trendalgo.device.views.scan_bt_ohlcvt_row import build_ohlcvt_block
from trendalgo.device.views.scan_bt_settings_dialog import ScanBacktestSettingsDialog


def test_download_button_shows_progress_and_ack(tmp_path: Path, qtbot: QtBot, monkeypatch) -> None:
    ack: list[str] = []

    def fake_download(dest: Path, *, on_progress=None, cancel=None):  # noqa: ANN001
        del cancel
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / "Kraken_OHLCVT_Full.zip"
        if on_progress is not None:
            on_progress("Part 1/5: downloading", 0.1)
            on_progress("Part 3/5: downloading", 0.5)
            on_progress("Joining ZIP parts…", 0.92)
            on_progress("OHLCVT archive ready", 1.0)
        out.write_bytes(b"PK\x03\x04fake")
        return out

    monkeypatch.setattr(
        "trendalgo.device.views.scan_bt_ohlcvt_row.download_full_archive",
        fake_download,
    )

    def fake_info(parent, title, text, *args, **kwargs):  # noqa: ANN001
        del parent, args, kwargs
        ack.append(f"{title}\n{text}")
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "information", staticmethod(fake_info))

    host, path_edit, _tip, status, bar = build_ohlcvt_block(
        None,  # type: ignore[arg-type]
        root=tmp_path,
        initial_path="",
        auto_tip=True,
    )
    qtbot.addWidget(host)
    btn = host.findChild(QPushButton, "ohlcvtDownload")
    assert btn is not None
    assert isinstance(bar, QProgressBar)
    assert bar.isHidden()

    btn.click()
    qtbot.waitUntil(lambda: bool(ack), timeout=5000)
    qtbot.waitUntil(lambda: bar.value() == 100, timeout=2000)
    thread = getattr(host, "_ohlcvt_thread", None)
    if thread is not None:
        qtbot.waitUntil(thread.isFinished, timeout=3000)

    assert path_edit.text().endswith("Kraken_OHLCVT_Full.zip")
    assert Path(path_edit.text()).is_file()
    assert S.SCAN_BT_OHLCVT_DOWNLOAD_ACK_TITLE in ack[0]
    assert "Kraken_OHLCVT_Full.zip" in ack[0]
    # Fake ZIP has no MANIFEST → status falls back to missing/ready copy after refresh.
    assert status.text()
    assert bar.isHidden() is False
    assert bar.value() == 100


def test_settings_dialog_exposes_progress_bar(tmp_path: Path, qtbot: QtBot) -> None:
    dlg = ScanBacktestSettingsDialog(tmp_path, n_coins=1)
    qtbot.addWidget(dlg)
    assert dlg._ohlcvt_bar.objectName() == "ohlcvtProgress"
    assert dlg.findChild(QPushButton, "ohlcvtDownload") is not None
