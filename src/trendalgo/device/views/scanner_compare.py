"""Compare bar and side-by-side dialog for the Opportunity scanner."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.lts_scan_model import cell_gain, dash


class ScannerCompareBar(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("compareBar")
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        self._label = QLabel(S.SCANNER_COMPARE_EMPTY)
        self._label.setObjectName("hint")
        self.compare_btn = QPushButton(S.SCANNER_COMPARE_BTN)
        self.clear_btn = QPushButton(S.SCANNER_COMPARE_CLEAR)
        row.addWidget(self._label, 1)
        row.addWidget(self.compare_btn)
        row.addWidget(self.clear_btn)

    def set_pairs(self, pairs: set[str]) -> None:
        if pairs:
            self._label.setText(S.SCANNER_COMPARE.format(pairs=", ".join(sorted(pairs))))
        else:
            self._label.setText(S.SCANNER_COMPARE_EMPTY)


def show_compare_dialog(
    parent: QWidget,
    coins: list[dict[str, Any]],
    pairs: set[str],
) -> None:
    selected = [c for c in coins if str(c.get("pair") or c.get("symbol")) in pairs]
    if len(selected) < 2:
        return
    left, right = selected[0], selected[1]
    dialog = QDialog(parent)
    dialog.setWindowTitle(S.SCANNER_COMPARE_DIALOG)
    layout = QVBoxLayout(dialog)
    columns = QHBoxLayout()
    columns.addWidget(_side(left), 1)
    columns.addWidget(_side(right), 1)
    layout.addLayout(columns)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.exec()


def _side(coin: dict[str, Any]) -> QFrame:
    frame = QFrame()
    frame.setObjectName("panel")
    layout = QVBoxLayout(frame)
    symbol = str(coin.get("symbol") or "")
    layout.addWidget(QLabel(symbol))
    for title, value in (
        ("7D%", dash(cell_gain(coin, "7d"), pct=True)),
        ("30D%", dash(cell_gain(coin, "30d"), pct=True)),
        ("Best BT", dash(coin.get("bot_best_net_pct"), pct=True)),
        ("Bot vs B&H", dash(coin.get("bot_vs_bh_pct"), pct=True)),
        ("Uniformity", dash(coin.get("uniformity_score"))),
        ("24H Vol", dash(coin.get("volume_24h"), money=True)),
    ):
        layout.addWidget(QLabel(f"{title}: {value}"))
    return frame
