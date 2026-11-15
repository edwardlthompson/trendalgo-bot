"""Shared Scanner / Backtest Settings popup: TFs, TA list, ETA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.backtest.heartbeat_tf import (
    HEARTBEAT_TIMEFRAMES,
    SUBHOUR_TIMEFRAMES,
    comparable_scan_timeframes,
    is_subhour_tf,
    needs_1m_base,
)
from trendalgo.device import strings as S
from trendalgo.device.scan_bt_prefs import (
    ScanBtPrefs,
    bands_mix_ready,
    clamp_sauce_top_n,
    enabled_strategies,
    journal_started_date,
    load_scan_bt_prefs,
    resolve_ohlcvt_path,
    save_scan_bt_prefs,
    selected_timeframes,
)
from trendalgo.device.scan_time_history import estimate_label, load_history
from trendalgo.device.scanner_signal_sets import BT_SET_ALL_TA
from trendalgo.device.views.scan_bt_ohlcvt_row import build_ohlcvt_block, set_ohlcvt_journal_started
from trendalgo.device.views.scan_bt_settings_sections import (
    build_chrome,
    build_extras,
    build_results_view,
    build_ta_body,
    build_tf_host,
    wrap_section,
)
from trendalgo.market.kraken_ohlcvt_copy import format_subhour_mix_note
from trendalgo.market.kraken_ohlcvt_meta import read_archive_coverage, today_utc

_SCREEN_GUTTER_PX = 24


class ScanBacktestSettingsDialog(QDialog):
    def __init__(
        self,
        root: Path,
        *,
        n_coins: int = 1,
        parent: QWidget | None = None,
        interval_minutes: int = 60,
        heatmap_enabled: bool = False,
        min_volume_usd: float = 0.0,
        scan_exchanges: list[str] | None = None,
        exchange_options: list[tuple[str, str]] | None = None,
        chrome_out: dict[str, Any] | None = None,
        results_heatmap: bool | None = None,
        results_perfect: bool | None = None,
        results_out: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = root
        self._n_coins = max(1, int(n_coins))
        self._chrome_out = chrome_out
        self._results_out = results_out
        self._results_heatmap: QCheckBox | None = None
        self._results_perfect: QCheckBox | None = None
        self.setWindowTitle(S.SCAN_BT_SETTINGS_TITLE)
        self.setMinimumWidth(720)
        prefs = load_scan_bt_prefs(root)
        ohlcvt_initial = resolve_ohlcvt_path(root, prefs.ohlcvt_path)
        self._journal_started = journal_started_date(prefs, root=root) or today_utc()
        self._mix = bands_mix_ready(prefs, root=root)

        self._eta = QLabel()
        self._eta.setObjectName("hint")
        self._eta.setWordWrap(True)
        self._eta.setToolTip(S.SCAN_BT_ETA_HINT)

        ohlcvt_host, self._ohlcvt_path, self._ohlcvt_tip, _st, self._ohlcvt_bar = (
            build_ohlcvt_block(
                self,
                root=root,
                initial_path=ohlcvt_initial,
                auto_tip=bool(prefs.ohlcvt_auto_tip),
                journal_started=self._journal_started,
                include_title=False,
            )
        )
        self._ohlcvt_host = ohlcvt_host
        self._ohlcvt_path.textChanged.connect(self._on_ohlcvt_path_changed)

        checked = set(selected_timeframes(prefs, root=root))
        tf_host, self._tf_boxes, self._sub_note = build_tf_host(
            checked=checked,
            on_tf_toggled=self._on_tf_toggled,
            on_set_tfs=self._set_tfs,
        )
        self._refresh_subhour_note(ohlcvt_initial)

        ta_body, _search, self._ta_list = build_ta_body(
            denylist=set(prefs.strategy_denylist),
            on_changed=self._refresh_eta,
        )
        extras, self._mc_with_scan, self._sauce_with_scan, self._sauce_top_n = build_extras(
            market_context=bool(prefs.market_context_with_scan),
            sauce_with=bool(prefs.sauce_with_scan),
            sauce_top_n=prefs.sauce_top_n,
            on_changed=self._refresh_eta,
        )
        chrome, self._every, self._heatmap, self._vol, self._exchange = build_chrome(
            interval_minutes=interval_minutes,
            heatmap_enabled=heatmap_enabled,
            min_volume_usd=min_volume_usd,
            exchange_options=exchange_options or [],
            scan_exchanges=scan_exchanges,
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_host = QWidget()
        cols = QHBoxLayout(scroll_host)
        cols.setContentsMargins(4, 4, 4, 4)
        cols.setSpacing(12)
        left = QVBoxLayout()
        right = QVBoxLayout()
        left.setSpacing(8)
        right.setSpacing(8)
        left.addWidget(wrap_section(S.SCAN_BT_CHROME_SECTION, chrome))
        if results_out is not None:
            results, self._results_heatmap, self._results_perfect = build_results_view(
                heatmap_enabled=bool(results_heatmap),
                perfect_only=bool(results_perfect),
            )
            left.addWidget(wrap_section(S.SCAN_BT_RESULTS_SECTION, results))
        left.addWidget(wrap_section(S.SCAN_BT_ETA_SECTION, self._eta))
        left.addWidget(wrap_section(S.SCAN_BT_OHLCVT_SECTION, ohlcvt_host))
        left.addWidget(wrap_section(S.SCAN_BT_EXTRAS_SECTION, extras))
        left.addStretch(1)
        right.addWidget(wrap_section(S.SCAN_BT_TF_SECTION, tf_host))
        right.addWidget(wrap_section(S.SCAN_BT_TA_SECTION, ta_body))
        right.addStretch(1)
        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        scroll.setWidget(scroll_host)

        body = QVBoxLayout(self)
        body.setSpacing(10)
        body.addWidget(scroll, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        body.addWidget(buttons)
        self._fit_screen_height()
        self._refresh_eta()

    def _fit_screen_height(self) -> None:
        """Near full available height with gutters above and below."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.setMinimumHeight(520)
            return
        geo = screen.availableGeometry()
        height = max(520, geo.height() - 2 * _SCREEN_GUTTER_PX)
        width = max(self.minimumWidth(), min(1100, geo.width() - 2 * _SCREEN_GUTTER_PX))
        x = geo.x() + max(0, (geo.width() - width) // 2)
        y = geo.y() + _SCREEN_GUTTER_PX
        self.setGeometry(x, y, width, height)

    def _refresh_subhour_note(self, path: str | None = None) -> None:
        raw = (path if path is not None else self._ohlcvt_path.text()).strip()
        note = format_subhour_mix_note(
            read_archive_coverage(raw) if raw else None,
            journal_started=self._journal_started,
        )
        self._sub_note.setText(note)
        for tf in SUBHOUR_TIMEFRAMES:
            box = self._tf_boxes.get(tf)
            if box is not None:
                box.setToolTip(note)
        set_ohlcvt_journal_started(self._ohlcvt_host, self._journal_started)

    def _on_ohlcvt_path_changed(self, _text: str = "") -> None:
        path = self._ohlcvt_path.text().strip()
        prefs = load_scan_bt_prefs(self._root)
        prefs.ohlcvt_path = path
        self._mix = bands_mix_ready(prefs, root=self._root)
        self._refresh_subhour_note(path)
        self._refresh_eta()

    def _on_tf_toggled(self, tf: str, checked: bool) -> None:
        if checked and not self._mix:
            clear = HEARTBEAT_TIMEFRAMES if is_subhour_tf(tf) else SUBHOUR_TIMEFRAMES
            for other in clear:
                box = self._tf_boxes.get(other)
                if box is None or not box.isChecked():
                    continue
                box.blockSignals(True)
                box.setChecked(False)
                box.blockSignals(False)
        self._refresh_eta()

    def _set_tfs(self, ids: tuple[str, ...], checked: bool) -> None:
        if checked and ids and not self._mix:
            clear = HEARTBEAT_TIMEFRAMES if is_subhour_tf(ids[0]) else SUBHOUR_TIMEFRAMES
            for other in clear:
                box = self._tf_boxes.get(other)
                if box is None:
                    continue
                box.blockSignals(True)
                box.setChecked(False)
                box.blockSignals(False)
        for tf in ids:
            box = self._tf_boxes.get(tf)
            if box is None or not box.isEnabled():
                continue
            box.blockSignals(True)
            box.setChecked(checked)
            box.blockSignals(False)
        self._refresh_eta()

    def _selected_tfs(self) -> list[str]:
        raw = [tf for tf, box in self._tf_boxes.items() if box.isChecked()]
        return list(comparable_scan_timeframes(raw, deep_1m=self._mix))

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
        started = self._journal_started or today_utc()
        save_scan_bt_prefs(
            self._root,
            ScanBtPrefs(
                timeframes=tfs,
                strategy_denylist=deny,
                bt_signal_set=BT_SET_ALL_TA,
                sauce_with_scan=bool(self._sauce_with_scan.isChecked()),
                sauce_top_n=clamp_sauce_top_n(self._sauce_top_n.value()),
                market_context_with_scan=bool(self._mc_with_scan.isChecked()),
                ohlcvt_path=self._ohlcvt_path.text().strip(),
                ohlcvt_auto_tip=bool(self._ohlcvt_tip.isChecked()),
                ohlcvt_journal_started=started.isoformat(),
            ),
        )
        if self._chrome_out is not None:
            self._every.interpretText()
            self._vol.interpretText()
            self._chrome_out["interval_minutes"] = int(self._every.value())
            self._chrome_out["heatmap_enabled"] = bool(self._heatmap.isChecked())
            self._chrome_out["min_volume_usd"] = float(self._vol.value())
            self._chrome_out["scan_exchanges"] = self._exchange.selected_ids()
        if self._results_out is not None and self._results_heatmap is not None:
            self._results_out["heatmap_enabled"] = bool(self._results_heatmap.isChecked())
            assert self._results_perfect is not None
            self._results_out["perfect_only"] = bool(self._results_perfect.isChecked())
        self.accept()


def open_scan_bt_settings(
    root: Path,
    *,
    n_coins: int = 1,
    parent: QWidget | None = None,
    interval_minutes: int = 60,
    heatmap_enabled: bool = False,
    min_volume_usd: float = 0.0,
    scan_exchanges: list[str] | None = None,
    exchange_options: list[tuple[str, str]] | None = None,
    chrome_out: dict[str, Any] | None = None,
    results_heatmap: bool | None = None,
    results_perfect: bool | None = None,
    results_out: dict[str, Any] | None = None,
) -> bool:
    dlg = ScanBacktestSettingsDialog(
        root,
        n_coins=n_coins,
        parent=parent,
        interval_minutes=interval_minutes,
        heatmap_enabled=heatmap_enabled,
        min_volume_usd=min_volume_usd,
        scan_exchanges=scan_exchanges,
        exchange_options=exchange_options,
        chrome_out=chrome_out,
        results_heatmap=results_heatmap,
        results_perfect=results_perfect,
        results_out=results_out,
    )
    dlg.setWindowModality(Qt.WindowModality.WindowModal)
    return dlg.exec() == QDialog.DialogCode.Accepted
