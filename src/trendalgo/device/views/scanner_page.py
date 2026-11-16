"""Opportunity scanner: Run scan, filters, dense table, logs."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from multiprocessing.pool import AsyncResult
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.debug_scan import (
    clear_scan_caches,
    debug_scan_enabled,
    log_debug_scan_publish,
)
from trendalgo.device.export_prefs import remember_export_dir
from trendalgo.device.lts_scan_model import (
    filter_coins,
    load_filters,
    load_lts_rows,
    load_watchlist,
    save_watchlist,
)
from trendalgo.device.rows import scan_caption
from trendalgo.device.scan_alerts import process_scan_alerts, toast_lines
from trendalgo.device.scan_job import scan_job
from trendalgo.device.scan_lock import ScanBusyError, scan_lock_held
from trendalgo.device.scan_model import (
    ScanUnavailableError,
    progress_line,
    scan_store_path,
)
from trendalgo.device.scan_progress import (
    clear_progress,
    consume_progress_events,
    read_progress,
)
from trendalgo.device.scanner_schedule import (
    FOREX_MIN_INTERVAL,
    clamp_interval_minutes,
    minutes_until,
    needs_autoscan_rearm,
    next_aligned_run,
)
from trendalgo.device.scanner_share import default_scanner_export_path, export_scanner_list_png
from trendalgo.device.scanner_sort import (
    COL_SORT_KEYS,
    DEFAULT_SORT_DIR,
    DEFAULT_SORT_KEY,
    sort_coins,
)
from trendalgo.device.stores import StoreReadError, read_snapshot
from trendalgo.device.time_display import load_use_utc
from trendalgo.device.views.board_paint import BoardPaintController
from trendalgo.device.views.buy_picks_pane import BuyPicksPane
from trendalgo.device.views.scan_progress_dialog import ScanProgressDialog, apply_main_blur
from trendalgo.device.views.scanner_chart_dialog import show_scanner_chart_dialog
from trendalgo.device.views.scanner_column_filter_row import ScannerColumnFilterRow
from trendalgo.device.views.scanner_filters import ScannerFilterBar
from trendalgo.device.views.scanner_results import show_results_dialog
from trendalgo.device.views.scanner_table import COLUMNS, fill_lts_table
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    clear_problem,
    problem_label,
    read_only_table,
    show_problem,
)
from trendalgo.device.workers import WorkerPool
from trendalgo.scanner.snapshot import QualifiedSnapshot

POLL_MS = 250
CAPTION_MS = 30_000
TAB_QUALIFIED, TAB_WATCH, TAB_LOGS = range(3)


class ScannerPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        parent: QWidget | None = None,
        *,
        lane: str = "crypto",
        on_create_bot: Callable[[dict[str, str], str], str] | None = None,
        on_spark_chart: Callable[[dict[str, Any], str], None] | None = None,
        on_toast: Callable[[str, str], None] | None = None,
        on_alerts_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = ctx.root
        lane_key = (lane or "crypto").strip().lower()
        if lane_key not in {"crypto", "tradfi", "forex"}:
            lane_key = "crypto"
        self._lane = lane_key  # type: ignore[assignment]
        self._own = scan_store_path(ctx.root, self._lane)
        # Crypto may merge host/shared scanner.db; TradFi/Forex never read crypto stores.
        if self._lane == "crypto":
            self._saved = ctx.databases["scanner"]
        else:
            self._saved = self._own
        self._candles = ctx.databases.get("candles")
        self._on_create_bot = on_create_bot
        self._on_spark_chart = on_spark_chart
        self._on_toast = on_toast
        self._on_alerts_changed = on_alerts_changed
        self._pool = WorkerPool(workers=1)
        self._pending: AsyncResult[Any] | None = None
        self._job_kind: str = "scan"
        self._scan_dialog: ScanProgressDialog | None = None
        self._coins: list[dict[str, Any]] = []
        self._shown: list[dict[str, Any]] = []
        self._sort_key = DEFAULT_SORT_KEY
        self._sort_dir = DEFAULT_SORT_DIR
        self._next_auto: datetime | None = None
        self._autoscan_enabled = True
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._poll)
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._on_auto_scan)
        self._caption_timer = QTimer(self)
        self._caption_timer.setInterval(CAPTION_MS)
        self._caption_timer.timeout.connect(self._refresh_auto_caption)

        self._filters = ScannerFilterBar()
        self._col_filters = ScannerColumnFilterRow()
        self._run = self._filters.run
        self._cancel = self._filters.cancel
        self._force_fresh_pending = False
        self._status = QLabel()
        self._problem = problem_label()
        self._caption = QLabel()
        self._caption.setObjectName("hint")
        self._caption.setWordWrap(True)
        empty_body = S.SCANNER_EMPTY_BODY
        if self._lane == "tradfi":
            empty_body = S.SCANNER_EMPTY_TRADFI_BODY
            self._table_title = S.SCANNER_TITLE_TRADFI
        elif self._lane == "forex":
            empty_body = S.SCANNER_EMPTY_FOREX_BODY
            self._table_title = S.SCANNER_TITLE_FOREX
        else:
            self._table_title = S.SCANNER_TITLE_CRYPTO
        self._empty_body_default = empty_body
        self._empty = EmptyState(
            S.SCANNER_EMPTY_TITLE,
            empty_body,
            center_action=self._lane != "crypto",
        )
        self._tabs = QTabBar()
        for label in (S.SCANNER_TAB_QUALIFIED, S.SCANNER_TAB_WATCH, S.SCANNER_TAB_LOGS):
            self._tabs.addTab(label)
        from trendalgo.device.results_view_prefs import load_results_prefs  # noqa: PLC0415

        view = load_results_prefs(self._root)
        self._buy_picks = BuyPicksPane(
            expanded=not view.buy_picks_collapsed,
            on_collapse=self._on_buy_picks_collapse,
        )
        self._table = read_only_table(S.SCANNER_LTS_HEADERS, self._table_title)
        self._table.setColumnCount(COLUMNS)
        self._col_filters.attach(self._table)
        self._table.horizontalHeader().sectionClicked.connect(self._on_header)
        self._table.horizontalHeader().sectionResized.connect(
            lambda *_a: self._col_filters.sync_control_widths(self._table)
        )
        self._board_progress = QProgressBar()
        self._board_progress.setObjectName("boardLoadProgress")
        self._board_progress.setTextVisible(False)
        self._board_progress.setFixedHeight(4)
        self._board_progress.hide()
        desk = (
            S.NAV_TRADFI
            if self._lane == "tradfi"
            else S.NAV_FOREX
            if self._lane == "forex"
            else S.NAV_CRYPTO
        )
        self._board_paint = BoardPaintController(
            table=self._table,
            tabs=self._tabs,
            progress=self._board_progress,
            status_set=lambda t: self._status.setText(t),
            desk_label=desk,
            on_desk_progress=self._on_desk_load_progress,
            parent=self,
        )
        self._logs = QPlainTextEdit()
        self._logs.setReadOnly(True)
        self._log_seq = 0
        layout = QVBoxLayout(self)
        layout.addWidget(self._filters)
        layout.addWidget(self._tabs)
        layout.addWidget(self._status)
        layout.addWidget(self._board_progress)
        layout.addWidget(self._problem)
        self._caption.hide()  # last-scan text is folded into the top filter row
        layout.addWidget(self._empty)
        layout.addWidget(self._buy_picks)
        layout.addWidget(self._table)
        layout.addWidget(self._logs)
        self._fill = TailFill(layout, self._table)
        saved = load_filters(self._root, lane=self._lane)
        if "heatmap_enabled" not in saved:
            saved = {**saved, "heatmap_enabled": view.heatmap_enabled}
        self._filters.load(saved)
        if self._lane == "forex":
            self._filters.set_interval_floor(FOREX_MIN_INTERVAL)
        self._col_filters.load(saved)
        self._sort_key = str(saved.get("sort_key") or DEFAULT_SORT_KEY)
        try:
            self._sort_dir = int(saved.get("sort_dir", DEFAULT_SORT_DIR))
        except (TypeError, ValueError):
            self._sort_dir = DEFAULT_SORT_DIR
        from trendalgo.device.lane_prefs import LaneId, load_lane_prefs

        self._lane_prefs = load_lane_prefs(self._root)
        lane_id: LaneId = self._lane  # type: ignore[assignment]
        self._filters.auto_scan.setChecked(self._lane_prefs.auto_scan(lane_id))
        if self._lane != "crypto":
            # Sauce Pan is available on TradFi/Forex; Pool Watch stays crypto-only.
            self._filters.pool_watch.hide()
        self._run.clicked.connect(lambda _checked=False: self._start())
        self._cancel.clicked.connect(lambda _checked=False: self._cancel_run())
        self._filters.refresh_prices.clicked.connect(lambda _checked=False: self._refresh_prices())
        self._filters.sauce_pan.clicked.connect(lambda _c=False: self._start_sauce_pan())
        self._filters.pool_watch.clicked.connect(lambda _c=False: self._open_pool_watch())
        self._filters.status_btn.clicked.connect(lambda _c=False: self._show_scan_status())
        if debug_scan_enabled():
            self._filters.set_force_fresh_in_more(True)
            self._filters.force_fresh.clicked.connect(
                lambda _checked=False: self._start_force_fresh()
            )
        self._wire_filter_signals()
        self._tabs.currentChanged.connect(lambda _index: self._show_tab())
        self._filters.share.clicked.connect(lambda _c=False: self._share_png())
        self.reload()
        self._boot_after_restore()
        self._caption_timer.start()
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state_changed)

    def _wire_filter_signals(self) -> None:
        self._filters.exchange.changed.connect(self._on_filter)
        self._filters.vol.editingFinished.connect(self._on_filter)
        self._filters.every.editingFinished.connect(self._on_filter)
        self._filters.heatmap.toggled.connect(lambda _c: self._on_filter())
        self._filters.settings.clicked.connect(lambda _c=False: self._open_scan_settings())
        self._col_filters.exchange.changed.connect(self._on_filter)
        self._refresh_scan_eta()
        for edit in (
            self._col_filters.gain_7d,
            self._col_filters.gain_30d,
            self._col_filters.best_bt,
            self._col_filters.health_min,
        ):
            edit.editingFinished.connect(self._on_filter)
            edit.returnPressed.connect(self._on_filter)
        for box in (
            self._col_filters.bot_vs_bh,
            self._col_filters.chart_dist_7d,
            self._col_filters.chart_dist_30d,
            self._col_filters.vol_accel,
            self._col_filters.vol24_min,
        ):
            box.currentIndexChanged.connect(lambda _i: self._on_filter())

    def reload(self) -> None:
        try:
            snapshot, from_pc = self._latest()
        except StoreReadError as exc:
            show_problem(self._problem, str(exc))
            return
        clear_problem(self._problem)
        self._coins = load_lts_rows(self._root, lane=self._lane)
        if not self._coins and snapshot is not None:
            from trendalgo.device.lts_scan_model import build_lts_rows

            eid = "kraken" if self._lane == "crypto" else self._lane
            self._coins = build_lts_rows(snapshot, enrich_charts=False, exchange_id=eid)
        if snapshot is None and not self._coins:
            self._caption.clear()
            body = self._empty_body_default
            if self._lane != "crypto":
                from trendalgo.device.alpaca_vault import has_alpaca_credentials

                if not has_alpaca_credentials():
                    body = S.SCAN_ALPACA_REQUIRED
            self._empty.set_text(S.SCANNER_EMPTY_TITLE, body)
        elif snapshot is not None:
            source = S.SCANNER_FROM_PC if from_pc else S.SCANNER_FROM_BOT
            caption = scan_caption(snapshot, use_utc=load_use_utc(self._root))
            self._caption.setText(f"{caption} {source}")
            self._empty.set_text(S.SCANNER_NONE_TITLE, S.SCANNER_NONE_BODY)
        else:
            self._caption.setText(S.SCANNER_FROM_PC)
            self._empty.set_text(S.SCANNER_NONE_TITLE, S.SCANNER_NONE_BODY)
        self._refresh_auto_caption()
        self._show_tab()

    def _on_filter(self) -> None:
        self._persist_filters()
        self._status.setText(S.SCANNER_FILTERS_SAVED)
        self._schedule_autoscan(reset=True)
        self._show_tab()

    def _open_scan_settings(self) -> None:
        from trendalgo.device.scan_venues import vaulted_scan_venues
        from trendalgo.device.support_matrix import checklist_brand
        from trendalgo.device.views.scan_bt_settings_dialog import open_scan_bt_settings

        chrome: dict[str, object] = {}
        venues = vaulted_scan_venues()
        options = [(v.exchange_id, checklist_brand(v.exchange_id, v.brand)) for v in venues]
        try:
            accepted = open_scan_bt_settings(
                self._root,
                n_coins=max(1, len(self._coins)),
                parent=self.window(),
                interval_minutes=int(self._filters.every.value()),
                heatmap_enabled=bool(self._filters.heatmap.isChecked()),
                min_volume_usd=float(self._filters.vol.value()),
                require_continuous_1h=bool(self._filters.require_continuous_1h()),
                scan_exchanges=list(self._filters.exchange.selected_ids()),
                exchange_options=options,
                chrome_out=chrome,
                lane=self._lane,
            )
        except Exception as exc:
            show_problem(self._problem, f"{S.SCAN_BT_SETTINGS}: {exc}")
            return
        if accepted:
            if "interval_minutes" in chrome:
                self._filters.every.setValue(int(chrome["interval_minutes"]))  # type: ignore[arg-type]
            if "heatmap_enabled" in chrome:
                self._filters.heatmap.setChecked(bool(chrome["heatmap_enabled"]))
            if "min_volume_usd" in chrome:
                self._filters.vol.setValue(float(chrome["min_volume_usd"]))  # type: ignore[arg-type]
            if "require_continuous_1h" in chrome:
                self._filters.set_require_continuous_1h(bool(chrome["require_continuous_1h"]))
            if "scan_exchanges" in chrome:
                selected = [str(x) for x in (chrome["scan_exchanges"] or [])]  # type: ignore[union-attr]
                self._filters.refresh_exchange_options(selected=selected)
            self._persist_filters()
            self._schedule_autoscan(reset=True)
            self._refresh_scan_eta()
            self._on_filter()
            self._status.setText(S.SCAN_BT_SETTINGS_SAVED)

    def _show_scan_status(self) -> None:
        from trendalgo.device.views.scanner_filters import show_scan_status_dialog

        show_scan_status_dialog(self._filters.status_text(), parent=self.window())

    def _open_pool_watch(self) -> None:
        from trendalgo.device.views.dex_watch_panel import open_dex_watch_dialog

        try:
            result = open_dex_watch_dialog(self._root, parent=self.window())
        except Exception as exc:
            show_problem(self._problem, f"{S.DEX_WATCH_RUN}: {exc}")
            return
        if result:
            self._status.setText(S.DEX_WATCH_STATUS.format(n=int(result.get("rows") or 0)))

    def _refresh_scan_eta(self) -> None:
        from trendalgo.backtest.heartbeat_tf import needs_1m_base
        from trendalgo.device.scan_bt_prefs import (
            enabled_strategies,
            load_scan_bt_prefs,
            selected_timeframes,
        )
        from trendalgo.device.scan_eta_filters import META_FUNNEL, projected_scan_coins
        from trendalgo.device.scan_time_history import estimate_label, load_history

        prefs = load_scan_bt_prefs(self._root)
        tfs = selected_timeframes(prefs)
        strats = enabled_strategies(prefs.strategy_denylist)
        saved = load_filters(self._root, lane=self._lane)
        funnel = saved.get(META_FUNNEL) if isinstance(saved.get(META_FUNNEL), dict) else None
        n_coins = projected_scan_coins(
            funnel,
            min_volume_usd=float(self._filters.vol.value()),
            require_continuous_1h=bool(self._filters.require_continuous_1h()),
            fallback_n=max(1, len(self._coins) or 1),
        )
        self._filters.set_eta_text(
            estimate_label(
                load_history(self._root),
                n_strategies=len(strats),
                n_timeframes=len(tfs),
                had_subhour=needs_1m_base(tfs),
                n_coins=n_coins,
                market_context=bool(prefs.market_context_with_scan),
                sauce_with_scan=bool(prefs.sauce_with_scan),
                sauce_top_n=int(prefs.sauce_top_n),
            )
        )

    def start_scan(self) -> None:
        self._start()

    def stop_autoscan(self) -> None:
        self._autoscan_enabled = False
        self._auto_timer.stop()
        self._caption_timer.stop()
        self._cancel_run()

    def _lane_auto_scan_on(self) -> bool:
        from trendalgo.device.lane_prefs import load_lane_prefs

        prefs = load_lane_prefs(self._root)
        return prefs.auto_scan(self._lane)  # type: ignore[arg-type]

    def _boot_after_restore(self) -> None:
        """Cold open: show last board and count down to the next aligned slot.

        Never start an Opportunity scan just because the app opened. Run scan
        (or the timer when the slot hits) is the only kickoff.
        """
        if not self._autoscan_enabled or not self._lane_auto_scan_on():
            return
        minutes = self._clamp_scan_interval(self._filters.every.value())
        self._next_auto = next_aligned_run(minutes)
        self._schedule_autoscan(reset=False)

    def _clamp_scan_interval(self, raw: int | float | None) -> int:
        floor = FOREX_MIN_INTERVAL if self._lane == "forex" else None
        return clamp_interval_minutes(raw, floor=floor)

    def _schedule_autoscan(self, *, reset: bool) -> None:
        if not self._autoscan_enabled or not self._lane_auto_scan_on():
            self._auto_timer.stop()
            return
        minutes = self._clamp_scan_interval(self._filters.every.value())
        if reset or self._next_auto is None:
            self._next_auto = next_aligned_run(minutes)
        delay_ms = max(1_000, int((self._next_auto - datetime.now(tz=UTC)).total_seconds() * 1000))
        self._auto_timer.start(delay_ms)
        self._refresh_auto_caption()

    def _on_auto_scan(self) -> None:
        if not self._autoscan_enabled or not self._lane_auto_scan_on():
            return
        if self._pending is not None:
            self._filters.set_auto_status_text(S.AUTOSCAN_PAUSED)
            self._schedule_autoscan(reset=False)
            return
        self._start()
        # One-shot timer dies on early _start returns unless we re-arm here.
        if self._pending is None:
            self._schedule_autoscan(reset=True)

    def _board_generated_at(self) -> datetime | None:
        try:
            snap, _from_pc = self._latest()
        except StoreReadError:
            return None
        return snap.generated_at if snap is not None else None

    def _maybe_rearm_autoscan(self) -> None:
        if not self._autoscan_enabled or self._pending is not None:
            return
        minutes = self._clamp_scan_interval(self._filters.every.value())
        if needs_autoscan_rearm(
            interval_minutes=minutes,
            last_generated=self._board_generated_at(),
            next_auto=self._next_auto,
            timer_active=self._auto_timer.isActive(),
        ):
            self._schedule_autoscan(reset=True)

    def _on_app_state_changed(self, state: object) -> None:
        try:
            from PySide6.QtCore import Qt

            if state == Qt.ApplicationState.ApplicationActive:
                self._maybe_rearm_autoscan()
        except (TypeError, AttributeError):
            return

    def _refresh_auto_caption(self) -> None:
        self._maybe_rearm_autoscan()
        parts: list[str] = []
        last = self._caption.text().strip()
        if last:
            parts.append(last)
        if not self._autoscan_enabled:
            self._filters.set_auto_status_text(" · ".join(parts))
            return
        if self._pending is not None:
            parts.append(S.AUTOSCAN_PAUSED)
        elif self._next_auto is None:
            parts.append(S.AUTOSCAN_OFF)
        else:
            parts.append(S.AUTOSCAN_NEXT.format(minutes=minutes_until(self._next_auto)))
        self._filters.set_auto_status_text(" · ".join(parts))

    def _on_header(self, section: int) -> None:
        key = COL_SORT_KEYS.get(section)
        if key is None:
            return
        if key == self._sort_key:
            self._sort_dir = -self._sort_dir
        else:
            self._sort_key = key
            self._sort_dir = DEFAULT_SORT_DIR
        self._persist_filters()
        self._show_tab()

    def _qualified_filtered_coins(
        self, coins: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Same filter_coins path as the Qualified tab (all column floors)."""
        base = list(self._coins if coins is None else coins)
        col = self._col_filters.dump()
        return filter_coins(
            base,
            exchanges=self._col_filters.exchange.filter_ids(),
            min_gain_7d=_floor_or_none(self._col_filters.gain_7d.floor()),
            min_gain_30d=_floor_or_none(self._col_filters.gain_30d.floor()),
            min_best_bt=_floor_or_none(self._col_filters.best_bt.floor()),
            bot_vs_bh_filter=str(col.get("bot_vs_bh_filter") or "") or None,
            chart_dist_max_7d=_opt_float(col.get("chart_dist_max_7d")),
            chart_dist_max_30d=_opt_float(col.get("chart_dist_max_30d")),
            health_min=_opt_float(col.get("health_min")),
            vol_accel_filter=str(col.get("vol_accel_filter") or "") or None,
            vol24_min=_opt_float(col.get("vol24_min")),
        )

    def _alert_floors(self) -> dict[str, float]:
        """Numeric Qualified-column floors for leave-reason copy."""
        col = self._col_filters.dump()
        scan = self._filters.dump()
        out: dict[str, float] = {}
        for key in (
            "min_gain_7d",
            "min_gain_30d",
            "min_gain_pct",
            "min_best_bt",
            "chart_dist_max_7d",
            "chart_dist_max_30d",
            "health_min",
            "vol24_min",
        ):
            val = _opt_float(col.get(key))
            if val is not None:
                out[key] = val
        val = _opt_float(scan.get("min_volume_usd"))
        if val is not None and val > 0:
            out["min_volume_usd"] = val
        if bool(scan.get("require_continuous_1h", True)):
            out["require_continuous_1h"] = 1.0
        return out

    def _needs_alpaca_cta(self) -> bool:
        if self._lane == "crypto":
            return False
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        from trendalgo.device.alpaca_vault import has_alpaca_credentials

        return not has_alpaca_credentials()

    def _refresh_alpaca_cta(self) -> None:
        if self._lane == "crypto":
            self._empty.set_action("", None, visible=False)
            return
        if self._needs_alpaca_cta():
            self._empty.set_text(S.SCANNER_EMPTY_TITLE, self._empty_body_default)
            self._empty.set_action(
                S.NOTIFY_ALPACA_WIZARD,
                self._open_alpaca_wizard,
                visible=True,
            )
        else:
            self._empty.set_action("", None, visible=False)

    def _on_desk_load_progress(self, label: str | None) -> None:
        win = self.window()
        setter = getattr(win, "set_desk_load_progress", None)
        if callable(setter):
            setter(self._lane, label)

    def _show_tab(self) -> None:
        tab = self._tabs.currentIndex()
        watch = set(load_watchlist(self._root, lane=self._lane))
        base = (
            [c for c in self._coins if _in_watch(c, watch)]
            if tab == TAB_WATCH
            else list(self._coins)
        )
        coins = self._qualified_filtered_coins(base)
        coins = sort_coins(coins, key=self._sort_key, direction=self._sort_dir)
        self._shown = coins
        show_table = tab in (TAB_QUALIFIED, TAB_WATCH)
        show_logs = tab == TAB_LOGS
        # Always keep the table shell + column filters on Qualified/Watch so chart-dist
        # and other widen-net controls stay available even when the scan qualifies none.
        has_source = bool(base)
        show_grid = show_table
        filter_miss = show_table and has_source and not coins
        empty_scan = show_table and not has_source
        show_buys = tab == TAB_QUALIFIED
        need_cta = self._needs_alpaca_cta()
        if need_cta and show_table:
            self._board_paint.cancel()
            self._refresh_alpaca_cta()
            self._empty.setVisible(True)
            self._buy_picks.setVisible(False)
            self._table.setVisible(False)
            self._col_filters.set_filters_visible(False)
            self._logs.setVisible(False)
            self._status.clear()
            return
        self._buy_picks.setVisible(show_buys)
        if show_buys:
            self._buy_picks.set_from_coins(coins)
        self._table.setVisible(show_grid)
        # Filters stay on the table; status carries the "no pairs" copy (not a blank page).
        self._empty.setVisible(False)
        self._refresh_alpaca_cta()
        self._col_filters.set_filters_visible(show_grid)
        self._logs.setVisible(show_logs)
        if show_logs:
            self._board_paint.cancel()
            self._fill.set_target(self._logs)
            self._fill.update(True)
        else:
            self._fill.set_target(self._table)
            self._fill.update(show_grid)
        if empty_scan:
            self._status.setText(S.SCANNER_NONE_TITLE)
        elif filter_miss:
            self._status.setText(S.SCANNER_FILTER_NONE_STATUS)
        elif (
            self._status.text()
            in {
                S.SCANNER_FILTER_NONE_STATUS,
                S.SCANNER_NONE_TITLE,
            }
            and not self._board_paint.busy
        ):
            self._status.clear()
        if show_grid:
            self._board_paint.cancel()
            keep_filters = self._col_filters.row_installed(self._table)
            if not keep_filters:
                self._col_filters.prepare_for_refill()
            # Text-only first — 400+ logo/spark widgets on the UI thread freezes the app.
            fill_lts_table(
                self._table,
                coins,
                watch=watch,
                sort_key=self._sort_key,
                sort_dir=self._sort_dir,
                heatmap=bool(self._filters.heatmap.isChecked()),
                filter_row=True,
                include_widgets=False,
                include_sparks=False,
                icon_root=self._root,
                lane=self._lane,
            )
            self._col_filters.install_row(self._table)
            if coins:
                self._board_paint.start(
                    coins,
                    filter_row=True,
                    watch=watch,
                    event_flags=self._event_flags_for(coins),
                    heatmap=bool(self._filters.heatmap.isChecked()),
                    on_watch=self._on_watch,
                    on_spark=self._on_spark,
                    on_events=self._on_coin_events,
                    on_results=self._on_results,
                    icon_root=self._root,
                    lane=self._lane,
                )

    def _on_watch(self, key: str, checked: bool) -> None:
        from trendalgo.device.scan_identity import drop_watch_aliases

        watch = load_watchlist(self._root, lane=self._lane)
        cleaned = drop_watch_aliases(watch, key)
        if checked:
            cleaned.append(key)
        save_watchlist(self._root, cleaned, lane=self._lane)
        self._show_tab()

    def _event_flags_for(self, coins: list[dict[str, Any]]) -> dict[str, bool]:
        from trendalgo.device.calendar.coin_window import has_coin_events
        from trendalgo.device.scan_identity import row_key

        out: dict[str, bool] = {}
        for coin in coins:
            key = row_key(coin) or str(coin.get("symbol") or "")
            if not key:
                continue
            flag = has_coin_events(self._root, coin)
            out[key] = flag
            sym = str(coin.get("symbol") or "")
            if sym:
                out[sym] = flag
        return out

    def _on_coin_events(self, coin: dict[str, Any]) -> None:
        from trendalgo.device.views.coin_event_timeline_dialog import open_coin_event_timeline

        open_coin_event_timeline(self._root, coin, parent=self.window())

    def _on_results(self, coin: dict[str, Any]) -> None:
        from trendalgo.device.results_pair_prefs import load_pair_filters

        pair = str(coin.get("pair") or coin.get("symbol") or "")
        show_results_dialog(
            self,
            coin,
            heatmap=bool(self._filters.heatmap.isChecked()),
            perfect_only=False,
            on_create_bot=self._on_create_bot,
            export_root=self._root,
            initial_filters=load_pair_filters(self._root, pair) or None,
        )

    def _on_spark(self, coin: dict[str, Any], window: str) -> None:
        if self._on_spark_chart is not None:
            self._on_spark_chart(coin, window)
            return
        show_scanner_chart_dialog(
            self,
            coin,
            window=window,
            candles_db=self._candles,
            price_only=True,
        )

    def _persist_filters(self) -> None:
        from trendalgo.device.scan_eta_filters import write_filters_ui

        payload = {**self._filters.dump(), **self._col_filters.dump()}
        payload["sort_key"] = self._sort_key
        payload["sort_dir"] = self._sort_dir
        write_filters_ui(self._root, payload, lane=self._lane)
        from trendalgo.device.results_view_prefs import (  # noqa: PLC0415
            ResultsViewPrefs,
            load_results_prefs,
            save_results_prefs,
        )

        prior = load_results_prefs(self._root)
        save_results_prefs(
            self._root,
            ResultsViewPrefs(
                heatmap_enabled=bool(self._filters.heatmap.isChecked()),
                perfect_only=prior.perfect_only,
                last_pair=prior.last_pair,
                results_dialog_width=prior.results_dialog_width,
                results_dialog_height=prior.results_dialog_height,
                results_dialog_maximized=prior.results_dialog_maximized,
                market_context_collapsed=prior.market_context_collapsed,
                buy_picks_collapsed=prior.buy_picks_collapsed,
            ),
        )

    def _on_buy_picks_collapse(self, collapsed: bool) -> None:
        from trendalgo.device.results_view_prefs import (  # noqa: PLC0415
            ResultsViewPrefs,
            load_results_prefs,
            save_results_prefs,
        )

        prior = load_results_prefs(self._root)
        save_results_prefs(
            self._root,
            ResultsViewPrefs(
                heatmap_enabled=prior.heatmap_enabled,
                perfect_only=prior.perfect_only,
                last_pair=prior.last_pair,
                results_dialog_width=prior.results_dialog_width,
                results_dialog_height=prior.results_dialog_height,
                results_dialog_maximized=prior.results_dialog_maximized,
                market_context_collapsed=prior.market_context_collapsed,
                buy_picks_collapsed=bool(collapsed),
            ),
        )

    def _latest(self) -> tuple[QualifiedSnapshot | None, bool]:
        sources = [(self._own, True)]
        if self._saved != self._own:
            sources.append((self._saved, False))
        found: list[tuple[QualifiedSnapshot, bool]] = []
        for path, from_pc in sources:
            snapshot = read_snapshot(path)
            if snapshot is not None:
                found.append((snapshot, from_pc))
        if not found:
            return None, False
        return max(found, key=lambda item: item[0].generated_at.timestamp())

    def _refresh_prices(self) -> None:
        """Expire OHLCV cache and re-run public (or keyed) scan — no keys required."""
        if self._pending is not None:
            return
        from trendalgo.device.price_cache_clear import clear_price_caches

        cleared = clear_price_caches(self._root)
        self._status.setText(f"{S.SCAN_REFRESH_PRICES}: cleared={','.join(cleared) or 'none'}")
        self._start()

    def _start_force_fresh(self) -> None:
        """Clear caches then live scan (public Kraken or keyed venues)."""
        if self._pending is not None or not debug_scan_enabled():
            return
        cleared = clear_scan_caches(self._root)
        self._force_fresh_pending = True
        self._status.setText(f"{S.SCAN_FORCE_FRESH_STARTING} cleared={','.join(cleared) or 'none'}")
        self._start(force_fresh=True)

    def _scan_mode_label(self) -> str:
        if self._lane != "crypto":
            return S.SCANNER_SOURCE_ALPACA
        from trendalgo.device.scan_venues import resolve_scan_exchange_ids

        venues = resolve_scan_exchange_ids(self._filters.dump())
        if venues:
            return S.SCANNER_SOURCE_KEYED.format(venues=", ".join(venues))
        return S.SCANNER_SOURCE_PUBLIC

    def _open_alpaca_wizard(self) -> None:
        from trendalgo.device.views.alpaca_wizard import AlpacaWizardDialog

        AlpacaWizardDialog(parent=self.window(), root=self._root).exec()
        self._refresh_alpaca_cta()
        self.reload()

    def _start_sauce_pan(self) -> None:
        """Sauce Pan manual cook — filtered Qualified + existing BT only (no TA scan)."""
        if self._pending is not None or self._scan_dialog is not None:
            show_problem(self._problem, S.SAUCE_PAN_BUSY)
            return
        from trendalgo.device.opportunity_sauce_job import (
            coins_eligible_for_sauce,
            run_manual_sauce_pan,
        )

        filtered = self._qualified_filtered_coins()
        eligible = coins_eligible_for_sauce(filtered)
        if not eligible:
            show_problem(self._problem, S.SAUCE_PAN_EMPTY)
            self._status.setText(S.SAUCE_PAN_EMPTY)
            return
        clear_problem(self._problem)
        clear_progress(self._root)
        self._logs.clear()
        self._log_seq = 0
        self._job_kind = "sauce"
        n = len(eligible)
        dialog = ScanProgressDialog(
            self.window(),
            title=S.SAUCE_PAN_TITLE,
            seed_lines=(S.SAUCE_PAN_RUN_TIP, S.SCAN_PROGRESS_STARTING),
            on_cancel=self._cancel_run,
            prior_s=0.0,
            initial_total=max(1, n),
            initial_pair="—",
            initial_pairs_total=None,
            count_label=S.SCAN_PROGRESS_STEPS,
        )
        self._scan_dialog = dialog
        self._pending = self._pool.submit(run_manual_sauce_pan, self._root, filtered, self._lane)
        self._filters.set_running(True)
        self._refresh_auto_caption()
        self._timer.start()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _start(self, *, force_fresh: bool = False) -> None:
        if self._pending is not None or self._scan_dialog is not None:
            return
        self._persist_filters()
        under_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        if self._lane != "crypto":
            from trendalgo.device.alpaca_vault import has_alpaca_credentials

            if not under_pytest and not has_alpaca_credentials():
                show_problem(self._problem, S.SCAN_ALPACA_REQUIRED)
                self._force_fresh_pending = False
                return
            if not under_pytest and scan_lock_held(self._root, self._lane):
                show_problem(self._problem, S.SCAN_BUSY)
                self._force_fresh_pending = False
                return
            clear_problem(self._problem)
            clear_progress(self._root)
            self._logs.clear()
            self._log_seq = 0
            if not force_fresh:
                self._force_fresh_pending = False
            self._job_kind = "scan"
            mode = self._scan_mode_label()
            n_coins = max(1, len(self._coins) or 1)
            dialog = ScanProgressDialog(
                self.window(),
                title=S.SCANNER_SCAN_TITLE.format(mode=mode),
                seed_lines=(
                    S.SCANNER_SCAN_SEED.format(
                        mode=mode,
                        n_tf=1,
                        n_strat=0,
                        n_coins=n_coins,
                    ),
                    S.SCAN_PROGRESS_STARTING,
                ),
                on_cancel=self._cancel_run,
                prior_s=0.0,
                initial_total=max(1, n_coins),
                initial_pair="—",
                initial_pairs_total=None,
                count_label=S.SCAN_PROGRESS_STEPS,
            )
            self._scan_dialog = dialog
            from trendalgo.device.lane_scan_job import forex_scan_job, tradfi_scan_job

            job = tradfi_scan_job if self._lane == "tradfi" else forex_scan_job
            self._pending = self._pool.submit(job, self._root)
            self._filters.set_running(True)
            self._filters.cancel.setEnabled(False)
            self._refresh_auto_caption()
            self._timer.start()
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return

        from trendalgo.backtest.heartbeat_tf import needs_1m_base
        from trendalgo.device.scan_bt_prefs import (
            enabled_strategies,
            load_scan_bt_prefs,
            selected_timeframes,
        )
        from trendalgo.device.scan_time_history import estimate_coin_seconds, load_history

        # Unit tests mock the worker pool; skip timeframe/strategy gates.
        prefs = load_scan_bt_prefs(self._root)
        tfs = selected_timeframes(prefs)
        strats = enabled_strategies(prefs.strategy_denylist)
        if not under_pytest and not tfs:
            show_problem(self._problem, S.SCAN_BT_NO_TFS)
            self._force_fresh_pending = False
            return
        if not under_pytest and not strats:
            show_problem(self._problem, S.SCAN_BT_NO_STRATEGIES)
            self._force_fresh_pending = False
            return
        if not under_pytest and scan_lock_held(self._root, self._lane):
            show_problem(self._problem, S.SCAN_BUSY)
            self._force_fresh_pending = False
            return
        clear_problem(self._problem)
        clear_progress(self._root)
        self._logs.clear()
        self._log_seq = 0
        if not force_fresh:
            self._force_fresh_pending = False
        self._job_kind = "scan"
        mode = self._scan_mode_label()
        n_coins = max(1, len(self._coins) or 1)
        had_subhour = needs_1m_base(tfs) if tfs else False
        from trendalgo.device.backtest_scan_eta import wall_coins_prior_s
        from trendalgo.device.scanner_all_ta_bt import all_ta_coin_workers

        per_coin = estimate_coin_seconds(
            load_history(self._root),
            n_strategies=len(strats) or 1,
            n_timeframes=len(tfs) or 1,
            had_subhour=had_subhour,
        )
        prior = wall_coins_prior_s(
            per_coin_s=per_coin, n_coins=n_coins, coin_workers=all_ta_coin_workers()
        )
        dialog = ScanProgressDialog(
            self.window(),
            title=S.SCANNER_SCAN_TITLE.format(mode=mode),
            seed_lines=(
                S.SCANNER_SCAN_SEED.format(
                    mode=mode,
                    n_tf=len(tfs) or 0,
                    n_strat=len(strats) or 0,
                    n_coins=n_coins,
                ),
                S.SCAN_PROGRESS_STARTING,
            ),
            on_cancel=self._cancel_run,
            prior_s=prior,
            initial_total=max(1, n_coins),
            initial_pair="—",
            initial_pairs_total=None,
            count_label=S.SCAN_PROGRESS_STEPS,
        )
        self._scan_dialog = dialog
        self._pending = self._pool.submit(scan_job, self._root)
        self._filters.set_running(True)
        self._filters.cancel.setEnabled(False)
        self._refresh_auto_caption()
        self._timer.start()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _poll(self) -> None:
        job = self._pending
        if job is None:
            self._timer.stop()
            return
        raw = read_progress(self._root)
        new_lines, self._log_seq = consume_progress_events(raw, self._log_seq)
        for entry in new_lines:
            self._logs.appendPlainText(entry)
        ready = bool(job.ready())
        if self._scan_dialog is not None:
            # Prefer progress_line for phase when present.
            phase = progress_line(raw)
            payload = dict(raw) if isinstance(raw, dict) else {}
            if phase and not payload.get("message"):
                payload["message"] = phase
            self._scan_dialog.update_progress(
                payload,
                worker_ready=ready,
                extra_log_lines=new_lines,
                append_phase_to_log=False,
            )
        if not ready:
            return
        self._timer.stop()
        self._pending = None
        job_kind = self._job_kind
        self._job_kind = "scan"
        # Clear modal blur immediately so the app is usable during board paint.
        self._close_scan_dialog()
        self._filters.set_running(False)
        problem = ""
        result: dict[str, Any] | None = None
        try:
            result = job.get(timeout=0)
        except ScanBusyError:
            problem = S.SCAN_BUSY
        except ScanUnavailableError:
            problem = S.SCAN_UNAVAILABLE
        except Exception as exc:
            from trendalgo.device.lane_scan_job import (
                AlpacaForexDataDeniedError,
                AlpacaKeysRequiredError,
            )

            if isinstance(exc, AlpacaForexDataDeniedError):
                problem = S.SCAN_FOREX_DATA_DENIED
            elif isinstance(exc, AlpacaKeysRequiredError):
                problem = S.SCAN_ALPACA_REQUIRED
            else:
                problem = (
                    S.SAUCE_PAN_FAILED.format(error=str(exc))
                    if job_kind == "sauce"
                    else S.SCAN_FAILED
                )

        self._tabs.setCurrentIndex(TAB_QUALIFIED)
        self.reload()
        if job_kind == "sauce":
            if problem:
                show_problem(self._problem, problem)
            elif isinstance(result, dict) and not result.get("ok"):
                show_problem(
                    self._problem,
                    str(result.get("message") or S.SAUCE_PAN_EMPTY),
                )
            else:
                self._status.setText(S.SAUCE_PAN_DONE)
                self._emit_scan_alerts()
            self._schedule_autoscan(reset=False)
            return
        source = ""
        if isinstance(result, dict):
            source = str(result.get("data_source") or "").strip()
        if not source:
            source = self._scan_mode_label().removeprefix("Source: ").strip()
        source_badge = S.SCANNER_SOURCE_BADGE.format(source=source) if source else ""
        if self._force_fresh_pending:
            updated = None
            try:
                snap, _from_pc = self._latest()
                if snap is not None:
                    updated = snap.generated_at.isoformat()
            except Exception:  # noqa: BLE001 — debug log only
                updated = None
            log_debug_scan_publish(self._root, updated_at=updated)
            if updated and not problem:
                done = f"{S.SCAN_DONE} DEBUG_SCAN updated_at={updated}"
                self._status.setText(f"{done} · {source_badge}" if source_badge else done)
            self._force_fresh_pending = False
        if problem:
            show_problem(self._problem, problem)
        else:
            if isinstance(result, dict) and int(result.get("pairs") or 0) == 0:
                skipped = int(result.get("skipped") or 0)
                self._status.setText(S.SCAN_LANE_EMPTY_RESULT.format(skipped=skipped))
            elif not self._status.text().startswith(S.SCAN_DONE) and not self._board_paint.busy:
                done = S.SCAN_DONE
                self._status.setText(f"{done} · {source_badge}" if source_badge else done)
            if isinstance(result, dict):
                timings = result.get("timings")
                if isinstance(timings, dict) and timings.get("total_s") is not None:
                    try:
                        self._filters.set_last_elapsed_s(float(timings["total_s"]))
                    except (TypeError, ValueError):
                        pass
            self._refresh_scan_eta()
            self._emit_scan_alerts()
        self._schedule_autoscan(reset=True)

    def _share_png(self) -> None:
        if not self._shown or not self._table.isVisible():
            QMessageBox.information(self, S.SCANNER_SHARE, S.SCANNER_SHARE_NEED_ROWS)
            return
        suggested = str(default_scanner_export_path(self._root, label="list"))
        chosen, _flt = QFileDialog.getSaveFileName(
            self, S.SCANNER_SHARE_DIALOG, suggested, S.SCANNER_SHARE_FILTER
        )
        if not chosen:
            return
        out = Path(chosen) if chosen.lower().endswith(".png") else Path(f"{chosen}.png")
        try:
            export_scanner_list_png(
                out,
                coins=self._shown,
                title=f"Scanner · {len(self._shown)} pairs",
                filters={**self._filters.dump(), **self._col_filters.dump()},
                heatmap=bool(self._filters.heatmap.isChecked()),
                sort_key=self._sort_key,
                sort_dir=self._sort_dir,
                icon_root=self._root,
                lane=self._lane,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, S.SCANNER_SHARE, str(exc))
            return
        remember_export_dir(self._root, out)
        note = S.SCANNER_SHARE_DONE.format(name=out.name, path=str(out.parent))
        QMessageBox.information(self, S.SCANNER_SHARE, note)

    def _emit_scan_alerts(self) -> None:
        from trendalgo.device.scanner_alerts_store import append_log_alert

        watch = load_watchlist(self._root, lane=self._lane)
        alertable = self._qualified_filtered_coins()
        events, _history = process_scan_alerts(
            self._root,
            coins=alertable,
            watchlist_pairs=watch,
            floors=self._alert_floors(),
            board_coins=list(self._coins),
        )
        append_log_alert(
            self._root,
            kind="scan_log",
            reason=(
                f"Scan finished: {len(self._coins)} qualified · {len(alertable)} after filters"
            ),
        )
        if self._on_alerts_changed is not None:
            self._on_alerts_changed()
        if self._on_toast is not None:
            for title, body in toast_lines(events, self._root):
                self._on_toast(title, body)

    def _cancel_run(self) -> None:
        self._timer.stop()
        self._pending = None
        self._job_kind = "scan"
        self._pool.cancel()
        self._close_scan_dialog()
        self._filters.set_running(False)
        self._status.setText(S.SCAN_CANCELLED)
        self._refresh_auto_caption()

    def _close_scan_dialog(self) -> None:
        dialog = self._scan_dialog
        self._scan_dialog = None
        apply_main_blur(self.window(), enabled=False)
        if dialog is None:
            return
        try:
            dialog.finish_and_close()
        except Exception:
            try:
                dialog.reject_cancel_close()
            except Exception:
                pass


def _in_watch(coin: dict[str, Any], watch: set[str]) -> bool:
    from trendalgo.device.scan_identity import coin_in_watchlist

    return coin_in_watchlist(coin, watch)


def _floor_or_none(raw: int | None) -> float | None:
    """Pass through typed floors including 0; blank stays None."""
    return None if raw is None else float(raw)


def _opt_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None
