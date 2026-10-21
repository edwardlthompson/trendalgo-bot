"""Shared Scanner / Backtest Settings popup: TFs, TA list, ETA, signal set."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES, SUBHOUR_TIMEFRAMES, needs_1m_base
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device import strings as S
from trendalgo.device.scan_bt_prefs import (
    ScanBtPrefs,
    enabled_strategies,
    load_scan_bt_prefs,
    save_scan_bt_prefs,
)
from trendalgo.device.scan_time_history import estimate_label, load_history
from trendalgo.device.scanner_signal_sets import (
    BT_SET_3COMMAS,
    BT_SET_ALL_TA,
    normalize_bt_signal_set,
)
from trendalgo.device.views.widgets import configure_combo_popup, field


class ScanBacktestSettingsDialog(QDialog):
    def __init__(
        self,
        root: Path,
        *,
        show_signal_set: bool = True,
        n_coins: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = root
        self._n_coins = max(1, int(n_coins))
        self.setWindowTitle(S.SCAN_BT_SETTINGS_TITLE)
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        prefs = load_scan_bt_prefs(root)

        self._eta = QLabel()
        self._eta.setObjectName("hint")
        self._eta.setWordWrap(True)

        self._signals: QComboBox | None = None
        if show_signal_set:
            self._signals = QComboBox()
            self._signals.addItem(S.SCANNER_SIGNALS_3COMMAS, BT_SET_3COMMAS)
            self._signals.addItem(S.SCANNER_SIGNALS_ALL_TA, BT_SET_ALL_TA)
            configure_combo_popup(self._signals)
            idx = self._signals.findData(normalize_bt_signal_set(prefs.bt_signal_set))
            self._signals.setCurrentIndex(idx if idx >= 0 else 0)

        self._tf_boxes: dict[str, QCheckBox] = {}
        tf_host = QWidget()
        tf_col = QVBoxLayout(tf_host)
        tf_col.setContentsMargins(0, 0, 0, 0)
        tf_col.setSpacing(4)
        checked = set(prefs.timeframes)
        tf_col.addWidget(self._tf_block_header(S.SCAN_BT_TF_SUBHOUR, SUBHOUR_TIMEFRAMES))
        for tf in SUBHOUR_TIMEFRAMES:
            box = QCheckBox(tf)
            box.setChecked(tf in checked)
            box.toggled.connect(lambda _c: self._refresh_eta())
            self._tf_boxes[tf] = box
            tf_col.addWidget(box)
        tf_col.addWidget(self._tf_block_header(S.SCAN_BT_TF_HOURS, HEARTBEAT_TIMEFRAMES))
        for tf in HEARTBEAT_TIMEFRAMES:
            box = QCheckBox(tf)
            box.setChecked(tf in checked if checked else True)
            box.toggled.connect(lambda _c: self._refresh_eta())
            self._tf_boxes[tf] = box
            tf_col.addWidget(box)
        tf_scroll = QScrollArea()
        tf_scroll.setWidgetResizable(True)
        tf_scroll.setWidget(tf_host)
        tf_scroll.setMinimumHeight(200)

        self._ta_search = QLineEdit()
        self._ta_search.setPlaceholderText(S.SCAN_BT_TA_SEARCH)
        self._ta_search.textChanged.connect(self._filter_ta)
        self._ta_list = QListWidget()
        deny = set(prefs.strategy_denylist)
        for name in all_strategies():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked if name in deny else Qt.CheckState.Checked)
            self._ta_list.addItem(item)
        self._ta_list.itemChanged.connect(lambda _i: self._refresh_eta())

        body = QVBoxLayout(self)
        body.setSpacing(10)
        if self._signals is not None:
            body.addWidget(field(S.SCANNER_FILTER_SIGNALS, self._signals))
        body.addWidget(QLabel(S.SCAN_BT_TF_TITLE))
        body.addWidget(tf_scroll)
        body.addWidget(self._eta)
        body.addWidget(QLabel(S.SCAN_BT_TA_TITLE))
        body.addWidget(self._ta_search)
        body.addWidget(self._ta_list, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        body.addWidget(buttons)
        self._refresh_eta()

    def _tf_block_header(self, title: str, tfs: tuple[str, ...]) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.addWidget(QLabel(title), 1)
        all_btn = QPushButton(S.SCAN_BT_SELECT_ALL)
        none_btn = QPushButton(S.SCAN_BT_SELECT_NONE)
        all_btn.clicked.connect(lambda _c=False, ids=tfs: self._set_tfs(ids, True))
        none_btn.clicked.connect(lambda _c=False, ids=tfs: self._set_tfs(ids, False))
        lay.addWidget(all_btn)
        lay.addWidget(none_btn)
        return row

    def _set_tfs(self, ids: tuple[str, ...], checked: bool) -> None:
        for tf in ids:
            box = self._tf_boxes.get(tf)
            if box is not None:
                box.setChecked(checked)
        self._refresh_eta()

    def _filter_ta(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self._ta_list.count()):
            item = self._ta_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _selected_tfs(self) -> list[str]:
        return [tf for tf, box in self._tf_boxes.items() if box.isChecked()]

    def _denylist(self) -> list[str]:
        out: list[str] = []
        for i in range(self._ta_list.count()):
            item = self._ta_list.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                out.append(item.text())
        return out

    def _refresh_eta(self) -> None:
        tfs = self._selected_tfs()
        deny = self._denylist()
        strats = enabled_strategies(deny)
        hist = load_history(self._root)
        self._eta.setText(
            estimate_label(
                hist,
                n_strategies=len(strats),
                n_timeframes=len(tfs),
                had_subhour=needs_1m_base(tfs),
                n_coins=self._n_coins,
            )
        )

    def _save(self) -> None:
        tfs = self._selected_tfs()
        if not tfs:
            self._eta.setText(S.SCAN_BT_NO_TFS)
            return
        deny = self._denylist()
        if not enabled_strategies(deny):
            self._eta.setText(S.SCAN_BT_NO_STRATEGIES)
            return
        signal = BT_SET_3COMMAS
        if self._signals is not None:
            signal = normalize_bt_signal_set(self._signals.currentData())
        save_scan_bt_prefs(
            self._root,
            ScanBtPrefs(timeframes=tfs, strategy_denylist=deny, bt_signal_set=signal),
        )
        self.accept()


def open_scan_bt_settings(
    root: Path,
    *,
    show_signal_set: bool = True,
    n_coins: int = 1,
    parent: QWidget | None = None,
) -> bool:
    dlg = ScanBacktestSettingsDialog(
        root, show_signal_set=show_signal_set, n_coins=n_coins, parent=parent
    )
    return dlg.exec() == QDialog.DialogCode.Accepted
