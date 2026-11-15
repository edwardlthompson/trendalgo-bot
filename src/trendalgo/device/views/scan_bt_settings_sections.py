"""Section builders for Scan/Backtest Settings dialog."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES, SUBHOUR_TIMEFRAMES
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device import strings as S
from trendalgo.device.scan_bt_prefs import SAUCE_TOP_N_MAX, SAUCE_TOP_N_MIN, clamp_sauce_top_n
from trendalgo.device.views.collapsible_section import CollapsibleSection


def wrap_section(title: str, widget: QWidget, *, expanded: bool = True) -> CollapsibleSection:
    sec = CollapsibleSection(title, expanded=expanded)
    sec.add_widget(widget)
    return sec


def build_tf_host(
    *,
    checked: set[str],
    on_tf_toggled: Callable[[str, bool], None],
    on_set_tfs: Callable[[tuple[str, ...], bool], None],
) -> tuple[QWidget, dict[str, QCheckBox], QLabel]:
    host = QWidget()
    col = QVBoxLayout(host)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(4)
    boxes: dict[str, QCheckBox] = {}
    col.addWidget(_tf_header(S.SCAN_BT_TF_SUBHOUR, SUBHOUR_TIMEFRAMES, on_set_tfs))
    note = QLabel()
    note.setObjectName("ohlcvtMixNote")
    note.setWordWrap(True)
    col.addWidget(note)
    for tf in SUBHOUR_TIMEFRAMES:
        box = QCheckBox(tf)
        box.setChecked(tf in checked)
        box.toggled.connect(lambda on, t=tf: on_tf_toggled(t, on))
        boxes[tf] = box
        col.addWidget(box)
    col.addWidget(_tf_header(S.SCAN_BT_TF_HOURS, HEARTBEAT_TIMEFRAMES, on_set_tfs))
    for tf in HEARTBEAT_TIMEFRAMES:
        box = QCheckBox(tf)
        box.setChecked(tf in checked if checked else True)
        box.toggled.connect(lambda on, t=tf: on_tf_toggled(t, on))
        boxes[tf] = box
        col.addWidget(box)
    return host, boxes, note


def build_ta_body(
    *,
    denylist: set[str],
    on_changed: Callable[[], None],
) -> tuple[QWidget, QLineEdit, QListWidget]:
    body = QWidget()
    col = QVBoxLayout(body)
    col.setContentsMargins(0, 0, 0, 0)
    search = QLineEdit()
    search.setPlaceholderText(S.SCAN_BT_TA_SEARCH)
    ta_list = QListWidget()
    for name in all_strategies():
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Unchecked if name in denylist else Qt.CheckState.Checked)
        ta_list.addItem(item)
    ta_list.itemChanged.connect(lambda _i: on_changed())
    search.textChanged.connect(lambda text: _filter_ta(ta_list, text))
    col.addWidget(_ta_header(ta_list, on_changed))
    col.addWidget(search)
    col.addWidget(ta_list)
    return body, search, ta_list


def build_extras(
    *,
    market_context: bool,
    sauce_with: bool,
    sauce_top_n: int,
    on_changed: Callable[[], None],
) -> tuple[QWidget, QCheckBox, QCheckBox, QSpinBox]:
    extras = QWidget()
    col = QVBoxLayout(extras)
    col.setContentsMargins(0, 0, 0, 0)
    mc = QCheckBox(S.MARKET_CTX_WITH_SCAN)
    mc.setChecked(bool(market_context))
    mc.setToolTip(S.MARKET_CTX_WITH_SCAN_TIP)
    mc.toggled.connect(lambda _c: on_changed())
    sauce = QCheckBox(S.SAUCE_PAN_WITH_SCAN)
    sauce.setChecked(bool(sauce_with))
    sauce.setToolTip(S.SAUCE_PAN_WITH_SCAN_TIP)
    sauce.toggled.connect(lambda _c: on_changed())
    top_n = QSpinBox()
    top_n.setRange(SAUCE_TOP_N_MIN, SAUCE_TOP_N_MAX)
    top_n.setValue(clamp_sauce_top_n(sauce_top_n))
    top_n.setToolTip(S.SAUCE_PAN_TOP_N_TIP)
    top_n.valueChanged.connect(lambda _v: on_changed())
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(QLabel(S.SAUCE_PAN_TOP_N))
    lay.addWidget(top_n)
    lay.addStretch(1)
    col.addWidget(mc)
    col.addWidget(sauce)
    col.addWidget(row)
    return extras, mc, sauce, top_n


def _tf_header(
    title: str,
    tfs: tuple[str, ...],
    on_set_tfs: Callable[[tuple[str, ...], bool], None],
) -> QWidget:
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 8, 0, 0)
    lay.addWidget(QLabel(title), 1)
    all_btn = QPushButton(S.SCAN_BT_SELECT_ALL)
    none_btn = QPushButton(S.SCAN_BT_SELECT_NONE)
    all_btn.clicked.connect(lambda _c=False, ids=tfs: on_set_tfs(ids, True))
    none_btn.clicked.connect(lambda _c=False, ids=tfs: on_set_tfs(ids, False))
    lay.addWidget(all_btn)
    lay.addWidget(none_btn)
    return row


def _ta_header(ta_list: QListWidget, on_changed: Callable[[], None]) -> QWidget:
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(QLabel(S.SCAN_BT_TA_TITLE), 1)
    all_btn = QPushButton(S.SCAN_BT_SELECT_ALL)
    none_btn = QPushButton(S.SCAN_BT_SELECT_NONE)
    all_btn.setObjectName("scanBtTaAll")
    none_btn.setObjectName("scanBtTaNone")

    def _set_all(checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        ta_list.blockSignals(True)
        try:
            for i in range(ta_list.count()):
                item = ta_list.item(i)
                if item is not None and not item.isHidden():
                    item.setCheckState(state)
        finally:
            ta_list.blockSignals(False)
        on_changed()

    all_btn.clicked.connect(lambda _c=False: _set_all(True))
    none_btn.clicked.connect(lambda _c=False: _set_all(False))
    lay.addWidget(all_btn)
    lay.addWidget(none_btn)
    return row


def _filter_ta(ta_list: QListWidget, text: str) -> None:
    needle = text.strip().lower()
    for i in range(ta_list.count()):
        item = ta_list.item(i)
        item.setHidden(bool(needle) and needle not in item.text().lower())
