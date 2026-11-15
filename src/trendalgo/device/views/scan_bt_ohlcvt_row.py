"""OHLCVT path + download controls for Scan/Backtest Settings."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.market.kraken_ohlcvt import archive_ready, clear_ohlcvt_caches
from trendalgo.market.kraken_ohlcvt_copy import format_ohlcvt_status
from trendalgo.market.kraken_ohlcvt_download import default_download_dir, download_full_archive
from trendalgo.market.kraken_ohlcvt_meta import read_archive_coverage


class _DownloadWorker(QObject):
    progress = Signal(str, float)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, dest: Path) -> None:
        super().__init__()
        self._dest = dest

    def run(self) -> None:
        try:

            def _cb(msg: str, frac: float) -> None:
                self.progress.emit(msg, float(frac))

            path = download_full_archive(self._dest, on_progress=_cb)
            self.finished.emit(str(path))
        except Exception as exc:  # noqa: BLE001 — surface to UI
            self.failed.emit(str(exc))


def build_ohlcvt_block(
    parent: QWidget,
    *,
    root: Path,
    initial_path: str,
    auto_tip: bool,
    journal_started: date | None = None,
    include_title: bool = True,
) -> tuple[QWidget, QLineEdit, QCheckBox, QLabel, QProgressBar]:
    host = QWidget(parent)
    col = QVBoxLayout(host)
    col.setContentsMargins(0, 0, 0, 0)
    if include_title:
        title = QLabel(S.SCAN_BT_OHLCVT_TITLE)
        title.setObjectName("sectionTitle")
        col.addWidget(title)
    path_edit = QLineEdit(initial_path)
    path_edit.setPlaceholderText(S.SCAN_BT_OHLCVT_PATH)
    browse = QPushButton(S.SCAN_BT_OHLCVT_BROWSE)
    download = QPushButton(S.SCAN_BT_OHLCVT_DOWNLOAD)
    download.setObjectName("ohlcvtDownload")
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(path_edit, 1)
    lay.addWidget(browse)
    lay.addWidget(download)
    col.addWidget(row)
    tip = QCheckBox(S.SCAN_BT_OHLCVT_TIP)
    tip.setChecked(bool(auto_tip))
    col.addWidget(tip)
    bar = QProgressBar()
    bar.setObjectName("ohlcvtProgress")
    bar.setRange(0, 100)
    bar.setValue(0)
    bar.setVisible(False)
    bar.setTextVisible(True)
    col.addWidget(bar)
    status = QLabel()
    status.setObjectName("ohlcvtStatus")
    status.setWordWrap(True)
    col.addWidget(status)
    host._journal_started = journal_started  # type: ignore[attr-defined]

    def _started() -> date | None:
        return getattr(host, "_journal_started", None)

    def _refresh_status() -> None:
        if bar.isVisible() and download.isEnabled() is False:
            return
        path = path_edit.text().strip()
        ready = archive_ready(path)
        if not ready:
            status.setText(S.SCAN_BT_OHLCVT_MISSING)
            return
        cov = read_archive_coverage(path)
        status.setText(format_ohlcvt_status(cov, journal_started=_started()))

    def _on_new_archive(path: str) -> None:
        clear_ohlcvt_caches(root)
        path_edit.setText(path)
        _refresh_status()

    def _browse() -> None:
        start = path_edit.text().strip() or str(default_download_dir(root))
        chosen, _ = QFileDialog.getOpenFileName(
            host,
            S.SCAN_BT_OHLCVT_BROWSE,
            start,
            "Kraken OHLCVT ZIP (*.zip)",
        )
        if chosen:
            _on_new_archive(chosen)

    def _on_progress(msg: str, frac: float) -> None:
        bar.setVisible(True)
        bar.setValue(int(round(max(0.0, min(1.0, frac)) * 100)))
        status.setText(msg)

    def _download() -> None:
        dest = default_download_dir(root)
        download.setEnabled(False)
        browse.setEnabled(False)
        bar.setVisible(True)
        bar.setValue(0)
        status.setText(S.SCAN_BT_OHLCVT_DOWNLOADING)
        thread = QThread(host)
        worker = _DownloadWorker(dest)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(_on_progress, Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(
            lambda p: _on_done(thread, p, ok=True),
            Qt.ConnectionType.QueuedConnection,
        )
        worker.failed.connect(
            lambda e: _on_done(thread, e, ok=False),
            Qt.ConnectionType.QueuedConnection,
        )
        host._ohlcvt_thread = thread  # type: ignore[attr-defined]
        host._ohlcvt_worker = worker  # type: ignore[attr-defined]
        thread.start()

    def _on_done(thread: QThread, payload: str, *, ok: bool) -> None:
        thread.quit()
        download.setEnabled(True)
        browse.setEnabled(True)
        if ok:
            clear_ohlcvt_caches(root)
            path_edit.setText(payload)
            bar.setValue(100)
            bar.setVisible(True)
            status.setText(S.SCAN_BT_OHLCVT_DOWNLOAD_DONE)
            QMessageBox.information(
                host,
                S.SCAN_BT_OHLCVT_DOWNLOAD_ACK_TITLE,
                S.SCAN_BT_OHLCVT_DOWNLOAD_ACK_BODY.format(path=payload),
            )
        else:
            bar.setValue(0)
            bar.setVisible(False)
            status.setText(S.SCAN_BT_OHLCVT_DOWNLOAD_FAIL.format(error=payload))
            QMessageBox.warning(
                host,
                S.SCAN_BT_OHLCVT_DOWNLOAD_FAIL_TITLE,
                S.SCAN_BT_OHLCVT_DOWNLOAD_FAIL.format(error=payload),
            )
        _refresh_status()

    browse.clicked.connect(_browse)
    download.clicked.connect(_download)
    path_edit.textChanged.connect(lambda _t: _refresh_status())
    _refresh_status()
    return host, path_edit, tip, status, bar


def set_ohlcvt_journal_started(host: QWidget, started: date | None) -> None:
    host._journal_started = started  # type: ignore[attr-defined]
    status = host.findChild(QLabel, "ohlcvtStatus")
    path_edit = host.findChild(QLineEdit)
    if status is None or path_edit is None:
        return
    path = path_edit.text().strip()
    if not archive_ready(path):
        status.setText(S.SCAN_BT_OHLCVT_MISSING)
        return
    status.setText(format_ohlcvt_status(read_archive_coverage(path), journal_started=started))
