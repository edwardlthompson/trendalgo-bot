"""Section builders for Scan/Backtest Settings dialog."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES, SUBHOUR_TIMEFRAMES
from trendalgo.backtest.ta_fleet import all_strategies
from trendalgo.device import strings as S
from trendalgo.device.scan_bt_prefs import SAUCE_TOP_N_MAX, SAUCE_TOP_N_MIN, clamp_sauce_top_n
from trendalgo.device.views.collapsible_section import CollapsibleSection
from trendalgo.device.views.exchange_checklist import ExchangeChecklist


def wrap_section(
    title: str,
    widget: QWidget,
    *,
    expanded: bool = True,
    expanding: bool = False,
) -> CollapsibleSection:
    sec = CollapsibleSection(title, expanded=expanded, expanding=expanding)
    sec.add_widget(widget, stretch=1 if expanding else 0)
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
    body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    col = QVBoxLayout(body)
    col.setContentsMargins(0, 0, 0, 0)
    search = QLineEdit()
    search.setPlaceholderText(S.SCAN_BT_TA_SEARCH)
    ta_list = QListWidget()
    ta_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    ta_list.setMinimumHeight(240)
    for name in all_strategies():
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Unchecked if name in denylist else Qt.CheckState.Checked)
        ta_list.addItem(item)
    ta_list.itemChanged.connect(lambda _i: on_changed())
    search.textChanged.connect(lambda text: _filter_ta(ta_list, text))
    col.addWidget(_ta_header(ta_list, on_changed))
    col.addWidget(search)
    col.addWidget(ta_list, 1)
    return body, search, ta_list


def build_chrome(
    *,
    interval_minutes: int,
    min_interval_minutes: int = 60,
    heatmap_enabled: bool,
    exchange_options: Sequence[tuple[str, str]],
    scan_exchanges: Sequence[str] | None,
) -> tuple[QWidget, QSpinBox, QCheckBox, ExchangeChecklist]:
    """Schedule + exchange + Color ranks (Auto-scan lives on each desk tab)."""
    host = QWidget()
    col = QVBoxLayout(host)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(8)
    note = QLabel(S.SCANNER_RESEARCH_HINT)
    note.setObjectName("hint")
    note.setWordWrap(True)
    col.addWidget(note)

    exchange = ExchangeChecklist()
    exchange.setToolTip(S.SCANNER_RESEARCH_HINT)
    exchange.set_options(list(exchange_options), selected=list(scan_exchanges or []))
    ex_row = QWidget()
    ex_lay = QHBoxLayout(ex_row)
    ex_lay.setContentsMargins(0, 0, 0, 0)
    ex_lay.addWidget(QLabel(S.SCANNER_FILTER_EXCHANGE))
    ex_lay.addWidget(exchange, 1)
    col.addWidget(ex_row)

    every_row = QWidget()
    every_lay = QHBoxLayout(every_row)
    every_lay.setContentsMargins(0, 0, 0, 0)
    every_lay.addWidget(QLabel(S.SCANNER_FILTER_EVERY))
    every = QSpinBox()
    floor = max(1, int(min_interval_minutes))
    every.setRange(floor, 1440)
    every.setSuffix(" min")
    every.setValue(max(floor, min(1440, int(interval_minutes))))
    if floor >= 90:
        every.setToolTip(S.FOREX_ALGOSPECIAL_INTERVAL_TIP)
    every_lay.addWidget(every)
    every_lay.addStretch(1)
    col.addWidget(every_row)

    heatmap = QCheckBox(S.SCANNER_COLOR_RANKS)
    heatmap.setChecked(bool(heatmap_enabled))
    col.addWidget(heatmap)

    return host, every, heatmap, exchange


def build_primary_filters(
    *,
    min_volume_usd: float,
    require_continuous_1h: bool = True,
    on_changed: Callable[[], None] | None = None,
) -> tuple[QWidget, QDoubleSpinBox, QCheckBox]:
    """Volume + continuous 1h (extensible primary-scan filter rows)."""
    host = QWidget()
    col = QVBoxLayout(host)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(8)

    vol_row = QWidget()
    vol_lay = QHBoxLayout(vol_row)
    vol_lay.setContentsMargins(0, 0, 0, 0)
    vol_lay.addWidget(QLabel(S.SCANNER_FILTER_VOL))
    vol = QDoubleSpinBox()
    vol.setRange(0, 1e12)
    vol.setDecimals(0)
    vol.setPrefix("$")
    vol.setSingleStep(100_000)
    vol.setValue(float(min_volume_usd))
    vol.setToolTip(S.SCANNER_FILTER_VOL_HINT)
    vol_lay.addWidget(vol)
    vol_lay.addStretch(1)
    col.addWidget(vol_row)
    vol_hint = QLabel(S.SCANNER_FILTER_VOL_HINT)
    vol_hint.setObjectName("hint")
    vol_hint.setWordWrap(True)
    col.addWidget(vol_hint)

    continuous = QCheckBox(S.SCANNER_FILTER_CONTINUOUS_1H)
    continuous.setToolTip(S.SCANNER_FILTER_CONTINUOUS_1H_TIP)
    continuous.setChecked(bool(require_continuous_1h))
    col.addWidget(continuous)

    if on_changed is not None:
        vol.valueChanged.connect(lambda _v: on_changed())
        continuous.toggled.connect(lambda _on: on_changed())
    return host, vol, continuous


def build_results_view(
    *,
    heatmap_enabled: bool,
    perfect_only: bool,
) -> tuple[QWidget, QCheckBox, QCheckBox]:
    """Backtest results view toggles (Color ranks, Perfect Strategies)."""
    host = QWidget()
    col = QVBoxLayout(host)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(6)
    heatmap = QCheckBox(S.SCANNER_COLOR_RANKS)
    heatmap.setChecked(bool(heatmap_enabled))
    perfect = QCheckBox(S.BACKTEST_PERFECT_ONLY)
    perfect.setChecked(bool(perfect_only))
    perfect.setToolTip(S.BACKTEST_PERFECT_HELP)
    col.addWidget(heatmap)
    col.addWidget(perfect)
    return host, heatmap, perfect


def build_lane_filters(
    *,
    lane: str,
    min_adv_usd: float,
    min_price: float,
    min_abs_gain_pct: float = 5.0,
    min_range_pct: float = 8.0,
    top_n: int = 120,
    on_changed: Callable[[], None] | None = None,
) -> tuple[
    QWidget,
    QDoubleSpinBox,
    QDoubleSpinBox,
    QDoubleSpinBox,
    QDoubleSpinBox,
    QSpinBox,
    list[QPushButton],
]:
    """TradFi move/range/top-N filters (+ optional ADV/price) with preset chips."""
    from trendalgo.device.lane_scan_filters import (  # noqa: PLC0415
        LaneScanFilters,
        apply_preset,
    )

    del lane  # TradFi-only builder; Forex desk omits this section.
    host = QWidget()
    col = QVBoxLayout(host)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(8)

    note = QLabel(S.LANE_FILTER_UNIVERSE_NOTE)
    note.setWordWrap(True)
    note.setToolTip(S.LANE_FILTER_UNIVERSE_NOTE)
    col.addWidget(note)

    preset_row = QWidget()
    preset_lay = QHBoxLayout(preset_row)
    preset_lay.setContentsMargins(0, 0, 0, 0)
    preset_lay.addWidget(QLabel(S.LANE_FILTER_PRESET))
    chips: list[QPushButton] = []
    labels = (
        ("wide", S.LANE_FILTER_PRESET_WIDE),
        ("balanced", S.LANE_FILTER_PRESET_BALANCED),
        ("tight", S.LANE_FILTER_PRESET_TIGHT),
        ("strict", S.LANE_FILTER_PRESET_STRICT),
    )

    abs_gain = QDoubleSpinBox()
    abs_gain.setRange(0, 100)
    abs_gain.setDecimals(1)
    abs_gain.setSuffix("%")
    abs_gain.setSingleStep(0.5)
    abs_gain.setValue(float(min_abs_gain_pct))
    abs_gain.setToolTip(S.LANE_FILTER_ABS_GAIN_TIP)

    range_pct = QDoubleSpinBox()
    range_pct.setRange(0, 200)
    range_pct.setDecimals(1)
    range_pct.setSuffix("%")
    range_pct.setSingleStep(0.5)
    range_pct.setValue(float(min_range_pct))
    range_pct.setToolTip(S.LANE_FILTER_RANGE_TIP)

    top = QSpinBox()
    top.setRange(0, 50_000)
    top.setSingleStep(10)
    top.setSpecialValueText(S.LANE_FILTER_TOP_N_OFF)
    top.setValue(int(top_n))
    top.setToolTip(S.LANE_FILTER_TOP_N_TIP)

    adv = QDoubleSpinBox()
    adv.setRange(0, 1e12)
    adv.setDecimals(0)
    adv.setPrefix("$")
    adv.setSingleStep(1_000_000)
    adv.setValue(float(min_adv_usd))
    adv.setToolTip(S.LANE_FILTER_ADV_TIP)

    price = QDoubleSpinBox()
    price.setRange(0, 1e6)
    price.setDecimals(2)
    price.setPrefix("$")
    price.setSingleStep(1.0)
    price.setValue(float(min_price))
    price.setToolTip(S.LANE_FILTER_PRICE_TIP)

    def _apply_chip(key: str) -> None:
        cur = LaneScanFilters(
            min_adv_usd=adv.value(),
            min_price=price.value(),
            min_abs_gain_pct=abs_gain.value(),
            min_range_pct=range_pct.value(),
            top_n=int(top.value()),
        )
        nxt = apply_preset("tradfi", key, cur)
        for box in (adv, price, abs_gain, range_pct, top):
            box.blockSignals(True)
        try:
            adv.setValue(nxt.min_adv_usd)
            price.setValue(nxt.min_price)
            abs_gain.setValue(nxt.min_abs_gain_pct)
            range_pct.setValue(nxt.min_range_pct)
            top.setValue(nxt.top_n)
        finally:
            for box in (adv, price, abs_gain, range_pct, top):
                box.blockSignals(False)
        if on_changed is not None:
            on_changed()

    for key, label in labels:
        btn = QPushButton(label)
        btn.setObjectName(f"laneFilterPreset_{key}")
        btn.setToolTip(S.LANE_FILTER_PRESET_TIP)
        btn.clicked.connect(lambda _c=False, k=key: _apply_chip(k))
        chips.append(btn)
        preset_lay.addWidget(btn)
    preset_lay.addStretch(1)
    col.addWidget(preset_row)

    def _row(label: str, tip: str, widget: QWidget) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(label)
        lab.setToolTip(tip)
        widget.setToolTip(tip)
        lay.addWidget(lab)
        lay.addWidget(widget)
        lay.addStretch(1)
        return row

    col.addWidget(_row(S.LANE_FILTER_ABS_GAIN, S.LANE_FILTER_ABS_GAIN_TIP, abs_gain))
    col.addWidget(_row(S.LANE_FILTER_RANGE, S.LANE_FILTER_RANGE_TIP, range_pct))
    col.addWidget(_row(S.LANE_FILTER_TOP_N, S.LANE_FILTER_TOP_N_TIP, top))
    col.addWidget(_row(S.LANE_FILTER_ADV, S.LANE_FILTER_ADV_TIP, adv))
    col.addWidget(_row(S.LANE_FILTER_PRICE, S.LANE_FILTER_PRICE_TIP, price))

    if on_changed is not None:
        for box in (adv, price, abs_gain, range_pct):
            box.valueChanged.connect(lambda _v: on_changed())
        top.valueChanged.connect(lambda _v: on_changed())
    return host, adv, price, abs_gain, range_pct, top, chips


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
