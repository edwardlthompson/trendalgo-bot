"""DEX pool-watch dialog (DEX-P2a) — honesty copy only when invoked."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.dex_watch_model import load_dex_watch_rows
from trendalgo.device.dex_watch_scan_job import dex_watch_scan_job


class DexWatchDialog(QDialog):
    """Run thin Uniswap/Base pool watch with on-demand disclaimer."""

    def __init__(self, root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = Path(root)
        self._result: dict[str, Any] | None = None
        self.setWindowTitle(S.DEX_WATCH_RUN)
        self.setModal(True)
        layout = QVBoxLayout(self)
        hint = QLabel(f"{S.DEX_WATCH_HINT}\n\n{S.DEX_BT_DISCLAIMER}")
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        layout.addWidget(hint)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._run = QPushButton(S.DEX_WATCH_RUN)
        self._run.setObjectName("dexWatchRun")
        self._run.clicked.connect(self._start)
        layout.addWidget(self._run)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.clicked.connect(self.accept)
        layout.addWidget(buttons)
        self._refresh_status()

    def _refresh_status(self) -> None:
        n = len(load_dex_watch_rows(self._root))
        self._status.setText(S.DEX_WATCH_STATUS.format(n=n) if n else S.DEX_WATCH_EMPTY)

    def _start(self) -> None:
        self._run.setEnabled(False)
        self._status.setText(S.DEX_WATCH_RUNNING)
        try:
            self._result = dex_watch_scan_job(self._root)
        except Exception as exc:  # noqa: BLE001 — surface in dialog
            self._run.setEnabled(True)
            self._status.setText(str(exc) or S.DEX_WATCH_ERROR)
            return
        self._run.setEnabled(True)
        self._refresh_status()

    def result_payload(self) -> dict[str, Any] | None:
        return self._result


def open_dex_watch_dialog(root: Path, parent: QWidget | None = None) -> dict[str, Any] | None:
    dlg = DexWatchDialog(root, parent=parent)
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    dlg.exec()
    return dlg.result_payload()


# Back-compat alias for imports that expected a panel widget name.
DexWatchPanel = DexWatchDialog
