"""Shared Scanner / Backtest Settings popup: TFs, TA list, ETA."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES, SUBHOUR_TIMEFRAMES, needs_1m_base
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device import strings as S
from trendalgo.device.scan_bt_prefs import (
    SAUCE_TOP_N_MAX,
    SAUCE_TOP_N_MIN,
    ScanBtPrefs,
    clamp_sauce_top_n,
    enabled_strategies,
    load_scan_bt_prefs,
    save_scan_bt_prefs,
)
from trendalgo.device.scan_time_history import estimate_label, load_history
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA


class ScanBacktestSettingsDialog(QDialog):
    def __init__(
        self,
        root: Path,
        *,
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
        self._eta.setToolTip(S.SCAN_BT_ETA_HINT)

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
        eta_cap = QLabel(S.SCAN_BT_ETA_TITLE)
        eta_cap.setObjectName("sectionTitle")
        body.addWidget(eta_cap)
        body.addWidget(self._eta)
        body.addWidget(QLabel(S.SCAN_BT_TF_TITLE))
        body.addWidget(tf_scroll)
        body.addWidget(self._ta_header())
        body.addWidget(self._ta_search)
        body.addWidget(self._ta_list, 1)

        self._mc_with_scan = QCheckBox(S.MARKET_CTX_WITH_SCAN)
        self._mc_with_scan.setChecked(bool(prefs.market_context_with_scan))
        self._mc_with_scan.setToolTip(S.MARKET_CTX_WITH_SCAN_TIP)
        self._mc_with_scan.toggled.connect(lambda _c: self._refresh_eta())
        sauce_title = QLabel(S.SAUCE_PAN_TITLE)
        sauce_title.setObjectName("sectionTitle")
        self._sauce_with_scan = QCheckBox(S.SAUCE_PAN_WITH_SCAN)
        self._sauce_with_scan.setChecked(bool(prefs.sauce_with_scan))
        self._sauce_with_scan.setToolTip(S.SAUCE_PAN_WITH_SCAN_TIP)
        self._sauce_with_scan.toggled.connect(lambda _c: self._refresh_eta())
        self._sauce_top_n = QSpinBox()
        self._sauce_top_n.setRange(SAUCE_TOP_N_MIN, SAUCE_TOP_N_MAX)
        self._sauce_top_n.setValue(clamp_sauce_top_n(prefs.sauce_top_n))
        self._sauce_top_n.setToolTip(S.SAUCE_PAN_TOP_N_TIP)
        self._sauce_top_n.valueChanged.connect(lambda _v: self._refresh_eta())
        sauce_n_row = QWidget()
        sauce_n_lay = QHBoxLayout(sauce_n_row)
        sauce_n_lay.setContentsMargins(0, 0, 0, 0)
        sauce_n_lay.addWidget(QLabel(S.SAUCE_PAN_TOP_N))
        sauce_n_lay.addWidget(self._sauce_top_n)
        sauce_n_lay.addStretch(1)
        body.addWidget(self._mc_with_scan)
        body.addWidget(sauce_title)
        body.addWidget(self._sauce_with_scan)
        body.addWidget(sauce_n_row)
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

    def _ta_header(self) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(S.SCAN_BT_TA_TITLE), 1)
        all_btn = QPushButton(S.SCAN_BT_SELECT_ALL)
        none_btn = QPushButton(S.SCAN_BT_SELECT_NONE)
        all_btn.setObjectName("scanBtTaAll")
        none_btn.setObjectName("scanBtTaNone")
        all_btn.clicked.connect(lambda _c=False: self._set_all_ta(True))
        none_btn.clicked.connect(lambda _c=False: self._set_all_ta(False))
        lay.addWidget(all_btn)
        lay.addWidget(none_btn)
        return row

    def _set_tfs(self, ids: tuple[str, ...], checked: bool) -> None:
        for tf in ids:
            box = self._tf_boxes.get(tf)
            if box is not None:
                box.setChecked(checked)
        self._refresh_eta()

    def _set_all_ta(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self._ta_list.blockSignals(True)
        try:
            for i in range(self._ta_list.count()):
                item = self._ta_list.item(i)
                if item is not None and not item.isHidden():
                    item.setCheckState(state)
        finally:
            self._ta_list.blockSignals(False)
        self._refresh_eta()

    def _filter_ta(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self._ta_list.count()):
            item = self._ta_list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().lower())

    def _selected_tfs(self) -> list[str]:
        return [tf for tf, box in self._tf_boxes.items() if box.isChecked()]

    def _denylist(self) -> list[str]:
        return [
            self._ta_list.item(i).text()
            for i in range(self._ta_list.count())
            if self._ta_list.item(i).checkState() != Qt.CheckState.Checked
        ]

    def _refresh_eta(self) -> None:
        tfs, deny = self._selected_tfs(), self._denylist()
        strats = enabled_strategies(deny)
        label = estimate_label(
            load_history(self._root),
            n_strategies=len(strats),
            n_timeframes=len(tfs),
            had_subhour=needs_1m_base(tfs),
            n_coins=self._n_coins,
            market_context=bool(self._mc_with_scan.isChecked()),
            sauce_with_scan=bool(self._sauce_with_scan.isChecked()),
            sauce_top_n=int(self._sauce_top_n.value()),
        )
        self._eta.setText(f"{label} · {len(strats)} TA · {len(tfs)} TF")

    def _save(self) -> None:
        tfs = self._selected_tfs()
        if not tfs:
            self._eta.setText(S.SCAN_BT_NO_TFS)
            return
        deny = self._denylist()
        if not enabled_strategies(deny):
            self._eta.setText(S.SCAN_BT_NO_STRATEGIES)
            return
        save_scan_bt_prefs(
            self._root,
            ScanBtPrefs(
                timeframes=tfs,
                strategy_denylist=deny,
                bt_signal_set=BT_SET_ALL_TA,
                sauce_with_scan=bool(self._sauce_with_scan.isChecked()),
                sauce_top_n=clamp_sauce_top_n(self._sauce_top_n.value()),
                market_context_with_scan=bool(self._mc_with_scan.isChecked()),
            ),
        )
        self.accept()


def open_scan_bt_settings(root: Path, *, n_coins: int = 1, parent: QWidget | None = None) -> bool:
    dlg = ScanBacktestSettingsDialog(root, n_coins=n_coins, parent=parent)
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    return dlg.exec() == QDialog.DialogCode.Accepted
