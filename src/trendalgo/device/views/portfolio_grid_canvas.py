"""Snap-to-grid canvas for Dashboard modules (move + BR corner resize)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget

from trendalgo.device.portfolio_grid_snap import (
    Rect,
    cell_size,
    find_free_or_swap,
    push_aside_for_resize,
    rect_to_pixels,
    snap_point,
    snap_resize,
)
from trendalgo.device.portfolio_layout_prefs import GridPrefs, Placement
from trendalgo.device.portfolio_module_catalog import effective_spec, title_for
from trendalgo.device.views.portfolio_module_chrome import ModuleChrome


class GridCanvas(QScrollArea):
    def __init__(
        self,
        *,
        on_placements_changed: Callable[[list[Placement]], None] | None = None,
        on_export_module: Callable[[str, QWidget], None] | None = None,
        on_remove_module: Callable[[str], None] | None = None,
        on_interaction_end: Callable[[str | None], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        # False: we size the surface ourselves so absolute modules are not crushed.
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setObjectName("dashCanvas")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Settings passes None for export/remove; Dashboard wires real handlers.
        self._surface = _GridSurface(
            on_placements_changed=on_placements_changed,
            on_export_module=on_export_module,
            on_remove_module=on_remove_module,
            on_need_size=self._fit_surface,
            on_interaction_end=on_interaction_end,
        )
        self.setWidget(self._surface)

    def _fit_surface(self, width: int, height: int) -> None:
        vw = max(self.viewport().width(), width, 400)
        h = max(height, self.viewport().height(), 400)
        self._surface.setMinimumSize(vw, h)
        self._surface.resize(vw, h)

    def set_grid(self, grid: GridPrefs) -> None:
        self._surface.set_grid(grid)

    def set_module_mins(self, module_mins: dict[str, tuple[int, int]]) -> None:
        self._surface.set_module_mins(module_mins)

    def set_modules(
        self,
        placements: list[Placement],
        bodies: dict[str, QWidget],
    ) -> None:
        self._surface.set_modules(placements, bodies)

    def set_edit_mode(self, editing: bool) -> None:
        self._surface.set_edit_mode(editing)

    def surface(self) -> QWidget:
        return self._surface

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._surface.relayout_for_width(max(self.viewport().width(), 400))


class _GridSurface(QFrame):
    def __init__(
        self,
        *,
        on_placements_changed: Callable[[list[Placement]], None] | None,
        on_export_module: Callable[[str, QWidget], None] | None,
        on_remove_module: Callable[[str], None] | None,
        on_need_size: Callable[[int, int], None],
        on_interaction_end: Callable[[str | None], None] | None = None,
    ) -> None:
        super().__init__()
        self._on_changed = on_placements_changed
        self._on_export = on_export_module
        self._on_remove = on_remove_module
        self._on_need_size = on_need_size
        self._on_interaction_end = on_interaction_end
        self._grid = GridPrefs()
        self._placements: dict[str, Placement] = {}
        self._chrome: dict[str, ModuleChrome] = {}
        self._drag_id: str | None = None
        self._drag_offset = QPoint()
        self._resize_id: str | None = None
        self._ghost: Rect | None = None
        self._relayouting = False
        self._edit_mode = False
        self._module_mins: dict[str, tuple[int, int]] = {}
        self.setObjectName("dashCanvas")
        self.setMouseTracking(True)

    def set_grid(self, grid: GridPrefs) -> None:
        self._grid = grid
        self.relayout_for_width(max(self.width(), 400))

    def set_module_mins(self, module_mins: dict[str, tuple[int, int]]) -> None:
        self._module_mins = dict(module_mins)

    def set_edit_mode(self, editing: bool) -> None:
        self._edit_mode = editing
        for chrome in self._chrome.values():
            chrome.set_edit_mode(editing)

    def set_modules(self, placements: list[Placement], bodies: dict[str, QWidget]) -> None:
        for chrome in list(self._chrome.values()):
            chrome.setParent(None)
            chrome.deleteLater()
        self._chrome.clear()
        self._placements = {p.id: p for p in placements}
        for placement in placements:
            body = bodies.get(placement.id)
            if body is None:
                continue
            chrome = ModuleChrome(
                placement.id,
                title_for(placement.id),
                body,
                on_export=self._export,
                on_remove=self._remove,
                edit_mode=self._edit_mode,
                parent=self,
            )
            chrome.handle.installEventFilter(self)
            chrome.resize_handle.installEventFilter(self)
            self._chrome[placement.id] = chrome
        self.relayout_for_width(max(self.width(), 400))

    def relayout_for_width(self, width: int) -> None:
        if self._relayouting:
            return
        self._relayouting = True
        try:
            max_bottom = max(
                (p.row + p.h for p in self._placements.values()),
                default=self._grid.rows,
            )
            cw, ch = cell_size(
                width,
                720,
                self._grid.cols,
                max(1, max_bottom),
                self._grid.gap_px,
                fixed_row_px=self._grid.row_px,
            )
            for mid, placement in self._placements.items():
                chrome = self._chrome.get(mid)
                if chrome is None:
                    continue
                rect = Rect(placement.col, placement.row, placement.w, placement.h)
                x, y, w, h = rect_to_pixels(rect, cw, ch, self._grid.gap_px)
                chrome.setGeometry(x, y, max(w, 120), max(h, 80))
                chrome.show()
                chrome.raise_()
            needed_h = int(max_bottom * (ch + self._grid.gap_px) + self._grid.gap_px)
            self._on_need_size(width, max(needed_h, 400))
            self.update()
        finally:
            self._relayouting = False

    def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        if not isinstance(event, QEvent):
            return False
        resize_id = next(
            (mid for mid, c in self._chrome.items() if c.resize_handle is watched),
            None,
        )
        move_id = next(
            (mid for mid, c in self._chrome.items() if c.handle is watched),
            None,
        )
        if resize_id is not None:
            return self._filter_resize(resize_id, event, isinstance(event, QMouseEvent))
        if move_id is not None:
            return self._filter_move(move_id, event, isinstance(event, QMouseEvent))
        return False

    def _filter_move(self, owner_id: str, event: object, is_mouse: bool) -> bool:
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        if self._resize_id is not None:
            return False
        if not is_mouse or not isinstance(event, QMouseEvent):
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_id = owner_id
                chrome = self._chrome[owner_id]
                self._drag_offset = event.position().toPoint()
                chrome.raise_()
                chrome.handle.setCursor(Qt.CursorShape.ClosedHandCursor)
                return True
        if event.type() == QEvent.Type.MouseMove:
            if self._drag_id == owner_id and event.buttons() & Qt.MouseButton.LeftButton:
                self._on_drag(event.globalPosition().toPoint())
                return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            if self._drag_id == owner_id:
                self._finish_drag()
                return True
        return False

    def _filter_resize(self, owner_id: str, event: object, is_mouse: bool) -> bool:
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QMouseEvent

        if self._drag_id is not None:
            return False
        if not is_mouse or not isinstance(event, QMouseEvent):
            return False
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self._resize_id = owner_id
                self._chrome[owner_id].raise_()
                return True
        if event.type() == QEvent.Type.MouseMove:
            if self._resize_id == owner_id and event.buttons() & Qt.MouseButton.LeftButton:
                self._on_resize(event.globalPosition().toPoint())
                return True
        if event.type() == QEvent.Type.MouseButtonRelease:
            if self._resize_id == owner_id:
                self._finish_resize()
                return True
        return False

    def paintEvent(self, event: object) -> None:  # noqa: N802
        super().paintEvent(event)
        if not (self._grid.show_grid or self._drag_id or self._resize_id):
            return
        painter = QPainter(self)
        pen = QPen(QColor(120, 120, 120, 80))
        pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        cw, ch = cell_size(
            self.width(),
            self.height(),
            self._grid.cols,
            self._grid.rows,
            self._grid.gap_px,
            fixed_row_px=self._grid.row_px,
        )
        bottom = max((p.row + p.h for p in self._placements.values()), default=self._grid.rows)
        for c in range(self._grid.cols + 1):
            x = int(c * (cw + self._grid.gap_px))
            painter.drawLine(x, 0, x, self.height())
        for r in range(bottom + 1):
            y = int(r * (ch + self._grid.gap_px))
            painter.drawLine(0, y, self.width(), y)
        if self._ghost is not None:
            gx, gy, gw, gh = rect_to_pixels(self._ghost, cw, ch, self._grid.gap_px)
            painter.fillRect(gx, gy, gw, gh, QColor(80, 140, 255, 60))

    def _on_drag(self, global_pos: QPoint) -> None:
        if self._drag_id is None:
            return
        chrome = self._chrome[self._drag_id]
        local = self.mapFromGlobal(global_pos) - self._drag_offset
        chrome.move(local)
        placement = self._placements[self._drag_id]
        cw, ch = cell_size(
            max(self.width(), 400),
            720,
            self._grid.cols,
            self._grid.rows,
            self._grid.gap_px,
            fixed_row_px=self._grid.row_px,
        )
        self._ghost = snap_point(
            local.x(),
            local.y(),
            cell_w=cw,
            cell_h=ch,
            gap_px=self._grid.gap_px,
            magnet_px=float(self._grid.magnet_px),
            cols=self._grid.cols,
            rows=max(self._grid.rows, placement.row + placement.h + 4),
            w=placement.w,
            h=placement.h,
        )
        self.update()

    def _finish_drag(self) -> None:
        mid = self._drag_id
        self._drag_id = None
        if mid is None:
            return
        chrome = self._chrome[mid]
        chrome.handle.setCursor(Qt.CursorShape.OpenHandCursor)
        ghost = self._ghost
        self._ghost = None
        if ghost is None:
            self.relayout_for_width(max(self.width(), 400))
            if self._on_interaction_end is not None:
                self._on_interaction_end(mid)
            return
        occupied = [(i, Rect(p.col, p.row, p.w, p.h)) for i, p in self._placements.items()]
        final, swap_id = find_free_or_swap(
            ghost,
            occupied,
            moving_id=mid,
            cols=self._grid.cols,
            rows=max(self._grid.rows, ghost.bottom + 2),
        )
        cur = self._placements[mid]
        if swap_id is not None:
            other = self._placements[swap_id]
            self._placements[swap_id] = Placement(
                id=swap_id, col=cur.col, row=cur.row, w=other.w, h=other.h
            )
        self._placements[mid] = Placement(id=mid, col=final.col, row=final.row, w=cur.w, h=cur.h)
        self.relayout_for_width(max(self.width(), 400))
        if self._on_changed is not None:
            self._on_changed(list(self._placements.values()))
        if self._on_interaction_end is not None:
            self._on_interaction_end(mid)

    def _on_resize(self, global_pos: QPoint) -> None:
        if self._resize_id is None:
            return
        mid = self._resize_id
        placement = self._placements[mid]
        local = self.mapFromGlobal(global_pos)
        origin = Rect(placement.col, placement.row, placement.w, placement.h)
        # Settings sections are not in the Dashboard catalog; honor module_mins directly.
        if mid in self._module_mins:
            min_w, min_h = self._module_mins[mid]
            max_w, max_h = self._grid.cols, 64
        else:
            spec = effective_spec(mid, self._module_mins)
            min_w = spec.min_w if spec else 2
            min_h = spec.min_h if spec else 2
            max_w = spec.max_w if spec else self._grid.cols
            max_h = spec.max_h if spec else 16
        rows = max(self._grid.rows, placement.row + max_h + 2, 24)
        cw, ch = cell_size(
            max(self.width(), 400),
            720,
            self._grid.cols,
            rows,
            self._grid.gap_px,
            fixed_row_px=self._grid.row_px,
        )
        ghost = snap_resize(
            origin,
            float(local.x()),
            float(local.y()),
            cell_w=cw,
            cell_h=ch,
            gap_px=self._grid.gap_px,
            magnet_px=float(self._grid.magnet_px),
            cols=self._grid.cols,
            rows=rows,
            min_w=min_w,
            min_h=min_h,
            max_w=max_w,
            max_h=max_h,
        )
        self._ghost = ghost
        occupied = [(i, Rect(p.col, p.row, p.w, p.h)) for i, p in self._placements.items()]
        preview = push_aside_for_resize(mid, ghost, occupied, cols=self._grid.cols)
        for pid, rect in preview.items():
            chrome = self._chrome.get(pid)
            if chrome is None:
                continue
            x, y, w, h = rect_to_pixels(rect, cw, ch, self._grid.gap_px)
            chrome.setGeometry(x, y, max(w, 120), max(h, 80))
        self.update()

    def _finish_resize(self) -> None:
        mid = self._resize_id
        self._resize_id = None
        if mid is None:
            return
        ghost = self._ghost
        self._ghost = None
        if ghost is None:
            self.relayout_for_width(max(self.width(), 400))
            return
        occupied = [(i, Rect(p.col, p.row, p.w, p.h)) for i, p in self._placements.items()]
        resolved = push_aside_for_resize(mid, ghost, occupied, cols=self._grid.cols)
        for pid, rect in resolved.items():
            self._placements[pid] = Placement(
                id=pid, col=rect.col, row=rect.row, w=rect.w, h=rect.h
            )
        needed = max((r.bottom for r in resolved.values()), default=ghost.bottom)
        if needed > self._grid.rows:
            self._grid.rows = min(96, needed)
        self.relayout_for_width(max(self.width(), 400))
        if self._on_changed is not None:
            self._on_changed(list(self._placements.values()))
        if self._on_interaction_end is not None:
            self._on_interaction_end(mid)

    def _export(self, module_id: str) -> None:
        chrome = self._chrome.get(module_id)
        if chrome is not None and self._on_export is not None:
            self._on_export(module_id, chrome)

    def _remove(self, module_id: str) -> None:
        if self._on_remove is not None:
            self._on_remove(module_id)
