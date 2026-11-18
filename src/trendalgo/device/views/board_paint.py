"""Viewport-lazy LTS board enrich — only visible rows get heavy cell widgets."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QProgressBar, QTabBar, QTableWidget, QWidget

from trendalgo.device import strings as S
from trendalgo.device.lane_icons import EquityIconFetcher, equity_cache_path
from trendalgo.device.views.scanner_table import enrich_lts_rows
from trendalgo.device.views.scanner_table_cells import COL_LOGO, LOGO_PX

_CHUNK = 8
_BUFFER = 4
_TICK_MS = 0

__all__ = ["BoardPaintController"]


class BoardPaintController(QObject):
    """Enrich widgets for the visible viewport only (survives desk hide)."""

    def __init__(
        self,
        *,
        table: QTableWidget,
        tabs: QTabBar,
        progress: QProgressBar,
        status_set: Callable[[str], None],
        desk_label: str,
        on_desk_progress: Callable[[str | None], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._table = table
        self._tabs = tabs
        self._progress = progress
        self._status_set = status_set
        self._desk_label = desk_label
        self._on_desk_progress = on_desk_progress
        self._coins: list[dict[str, Any]] = []
        self._enriched: set[int] = set()
        self._pending: list[int] = []
        self._filter_row = True
        self._watch: set[str] = set()
        self._flags: dict[str, bool] = {}
        self._heatmap = False
        self._on_watch: Callable[[str, bool], None] | None = None
        self._on_spark: Callable[[dict[str, Any], str], None] | None = None
        self._on_events: Callable[[dict[str, Any]], None] | None = None
        self._on_results: Callable[[dict[str, Any]], None] | None = None
        self._icon_root: Any | None = None
        self._lane = "crypto"
        self._icon_fetch: EquityIconFetcher | None = None
        self._qualified_base = S.SCANNER_TAB_QUALIFIED
        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._generation = 0
        bar = table.verticalScrollBar()
        bar.valueChanged.connect(lambda _v: self.schedule_visible())

    @property
    def busy(self) -> bool:
        return self._timer.isActive()

    def cancel(self) -> None:
        self._generation += 1
        self._timer.stop()
        self._coins = []
        self._enriched.clear()
        self._pending = []
        self._progress.hide()
        self._progress.setValue(0)
        self._tabs.setTabText(0, self._qualified_base)
        if self._on_desk_progress is not None:
            self._on_desk_progress(None)

    def start(
        self,
        coins: list[dict[str, Any]],
        *,
        filter_row: bool = True,
        watch: set[str] | None = None,
        event_flags: dict[str, bool] | None = None,
        heatmap: bool = False,
        on_watch: Callable[[str, bool], None] | None = None,
        on_spark: Callable[[dict[str, Any], str], None] | None = None,
        on_events: Callable[[dict[str, Any]], None] | None = None,
        on_results: Callable[[dict[str, Any]], None] | None = None,
        icon_root: Any | None = None,
        lane: str = "crypto",
    ) -> None:
        self.cancel()
        self._coins = list(coins)
        self._filter_row = filter_row
        self._watch = set(watch or ())
        self._flags = dict(event_flags or {})
        self._heatmap = bool(heatmap)
        self._on_watch = on_watch
        self._on_spark = on_spark
        self._on_events = on_events
        self._on_results = on_results
        self._icon_root = icon_root
        self._lane = lane
        self._ensure_icon_fetcher()
        if not self._coins:
            return
        self.schedule_visible()

    def schedule_visible(self) -> None:
        if not self._coins:
            return
        start, end = self._visible_range()
        for i in range(start, end):
            if i not in self._enriched and i not in self._pending:
                self._pending.append(i)
        # Kick logo downloads for the viewport immediately (don't wait for enrich).
        if self._icon_fetch is not None:
            syms = [
                str(self._coins[i].get("symbol") or "")
                for i in range(start, end)
                if 0 <= i < len(self._coins)
            ]
            self._icon_fetch.request(syms)
        self._report()
        if self._pending and not self._timer.isActive():
            self._timer.start()

    def _visible_range(self) -> tuple[int, int]:
        offset = 1 if self._filter_row else 0
        vp = self._table.viewport()
        top = self._table.indexAt(vp.rect().topLeft())
        bottom = self._table.indexAt(vp.rect().bottomLeft())
        if not top.isValid():
            first = 0
        else:
            first = max(0, top.row() - offset)
        if not bottom.isValid():
            last = min(len(self._coins), first + 24)
        else:
            last = min(len(self._coins), max(first + 1, bottom.row() - offset + 1))
        first = max(0, first - _BUFFER)
        last = min(len(self._coins), last + _BUFFER)
        return first, last

    def _tick(self) -> None:
        if not self._pending:
            self._finish_idle()
            return
        batch = self._pending[:_CHUNK]
        self._pending = self._pending[_CHUNK:]
        for i in batch:
            if i in self._enriched or i >= len(self._coins):
                continue
            enrich_lts_rows(
                self._table,
                self._coins,
                start=i,
                end=i + 1,
                filter_row=self._filter_row,
                watch=self._watch,
                event_flags=self._flags,
                heatmap=self._heatmap,
                on_watch=self._on_watch,
                on_spark=self._on_spark,
                on_events=self._on_events,
                on_results=self._on_results,
                icon_root=self._icon_root,
                lane=self._lane,
            )
            self._enriched.add(i)
            self._request_logo(self._coins[i])
        self._report()
        if not self._pending:
            self._finish_idle()

    def _ensure_icon_fetcher(self) -> None:
        if self._lane != "tradfi" or self._icon_root is None:
            self._icon_fetch = None
            return
        root = Path(str(self._icon_root))
        if self._icon_fetch is None or Path(str(getattr(self._icon_fetch, "_root", ""))) != root:
            self._icon_fetch = EquityIconFetcher(root, parent=self)
            self._icon_fetch.ready.connect(self._on_logo_ready)

    def _request_logo(self, coin: dict[str, Any]) -> None:
        if self._icon_fetch is None:
            return
        sym = str(coin.get("symbol") or "").strip().upper().split("/")[0]
        if sym:
            self._icon_fetch.request([sym])

    def _on_logo_ready(self, symbol: str) -> None:
        if self._icon_root is None or self._lane != "tradfi":
            return
        root = Path(str(self._icon_root))
        path = equity_cache_path(root, symbol)
        if not path.is_file():
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            return
        scaled = pix.scaled(
            LOGO_PX,
            LOGO_PX,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        offset = 1 if self._filter_row else 0
        needle = (symbol or "").strip().upper()
        for i, coin in enumerate(self._coins):
            if str(coin.get("symbol") or "").strip().upper().split("/")[0] != needle:
                continue
            host = self._table.cellWidget(i + offset, COL_LOGO)
            if host is None:
                # Row not enriched yet — lettermark/cache will apply on enrich.
                continue
            label = host.findChild(QLabel, "logoBadge") if isinstance(host, QWidget) else None
            if label is None:
                for child in host.findChildren(QLabel):
                    if child.property("logoSymbol") == needle:
                        label = child
                        break
            if label is not None:
                label.setPixmap(scaled)
                label.setText("")

    def _report(self) -> None:
        total = len(self._coins)
        done = len(self._enriched)
        if total <= 0:
            return
        pct = int(100 * done / total)
        if done < total and self._pending:
            self._progress.show()
            self._progress.setMaximum(total)
            self._progress.setValue(done)
            self._status_set(S.BOARD_LOAD_STATUS.format(done=done, total=total))
            self._tabs.setTabText(0, S.BOARD_LOAD_TAB.format(label=self._qualified_base, pct=pct))
            if self._on_desk_progress is not None:
                self._on_desk_progress(S.BOARD_LOAD_TAB.format(label=self._desk_label, pct=pct))
        else:
            self._progress.hide()
            self._tabs.setTabText(0, self._qualified_base)
            if self._on_desk_progress is not None:
                self._on_desk_progress(None)

    def _finish_idle(self) -> None:
        self._timer.stop()
        self._progress.hide()
        self._tabs.setTabText(0, self._qualified_base)
        if self._on_desk_progress is not None:
            self._on_desk_progress(None)
