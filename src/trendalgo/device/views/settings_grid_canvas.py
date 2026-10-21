"""Settings-tab grid canvas — content-aware pack, push on grow, rearrange after DnD."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QWidget

from trendalgo.device.portfolio_grid_snap import cell_size
from trendalgo.device.portfolio_layout_prefs import Placement
from trendalgo.device.settings_grid_fit import (
    cols_for_pixels,
    reflow_content_heights,
    rows_for_pixels,
)
from trendalgo.device.views.collapsible_section import CollapsibleSection
from trendalgo.device.views.portfolio_grid_canvas import GridCanvas
from trendalgo.device.views.portfolio_module_chrome import ModuleChrome


class SettingsGridCanvas(GridCanvas):
    """GridCanvas that sizes modules to content and packs siblings into gaps."""

    def __init__(
        self,
        *,
        titles: dict[str, str],
        on_placements_changed: Callable[[list[Placement]], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        self._titles = titles
        self._fitting = False
        self._fit_pending = False
        self._pin_id: str | None = None
        super().__init__(
            on_placements_changed=on_placements_changed,
            on_export_module=None,
            on_remove_module=None,
            on_interaction_end=self._after_interaction,
            parent=parent,
        )

    def set_modules(self, placements: list[Placement], bodies: dict[str, QWidget]) -> None:
        surface = self._surface
        for chrome in list(surface._chrome.values()):
            chrome.setParent(None)
            chrome.deleteLater()
        surface._chrome.clear()
        surface._placements = {p.id: p for p in placements}
        for placement in placements:
            body = bodies.get(placement.id)
            if body is None:
                continue
            title = self._titles.get(placement.id, placement.id)
            chrome = ModuleChrome(
                placement.id,
                title,
                body,
                on_export=None,
                on_remove=None,
                edit_mode=surface._edit_mode,
                content_aware=True,
                parent=surface,
            )
            chrome.handle.installEventFilter(surface)
            chrome.resize_handle.installEventFilter(surface)
            surface._chrome[placement.id] = chrome
            _wire_nested_toggles(body, self._on_section_toggled)
        self.schedule_fit_to_content()

    def _on_section_toggled(self, _expanded: bool = False) -> None:
        QApplication.processEvents()
        self.schedule_fit_to_content()

    def _after_interaction(self, module_id: str | None) -> None:
        self._pin_id = module_id
        self.schedule_fit_to_content()

    def schedule_fit_to_content(self) -> None:
        if self._fit_pending:
            return
        self._fit_pending = True
        QTimer.singleShot(0, self._run_scheduled_fit)

    def _run_scheduled_fit(self) -> None:
        self._fit_pending = False
        self.fit_to_content()

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.schedule_fit_to_content()

    def fit_to_content(self) -> None:
        """Measure each module w/h, pack (push on grow / fill gaps), relayout."""
        if self._fitting:
            return
        surface = self._surface
        if not surface._chrome:
            return
        self._fitting = True
        pin = self._pin_id
        self._pin_id = None
        try:
            width = max(self.viewport().width(), self.width(), 400)
            cols = max(1, surface._grid.cols)
            gap = surface._grid.gap_px
            cw, ch = cell_size(
                width,
                720,
                cols,
                max(1, surface._grid.rows),
                gap,
                fixed_row_px=surface._grid.row_px,
            )
            height_rows: dict[str, int] = {}
            width_cols: dict[str, int] = {}
            for mid, _placement in list(surface._placements.items()):
                chrome = surface._chrome.get(mid)
                if chrome is None:
                    continue
                need_w, need_h = _measure_chrome_size(chrome)
                chrome.setMinimumWidth(need_w)
                chrome.setMinimumHeight(need_h)
                chrome.setMaximumWidth(16777215)
                chrome.setMaximumHeight(16777215)
                height_rows[mid] = rows_for_pixels(need_h, ch, gap)
                width_cols[mid] = max(6, cols_for_pixels(need_w, cw, gap, cols=cols))
            # After drag/resize: keep the user's size as a floor so resize does not snap back.
            if pin is not None and pin in surface._placements:
                prev = surface._placements[pin]
                height_rows[pin] = max(height_rows.get(pin, 1), prev.h)
                width_cols[pin] = max(width_cols.get(pin, 1), prev.w)
            before = {p.id: (p.col, p.row, p.w, p.h) for p in surface._placements.values()}
            fitted = reflow_content_heights(
                list(surface._placements.values()),
                height_rows,
                cols=cols,
                pin_id=pin,
                width_cols=width_cols,
            )
            surface._placements = {p.id: p for p in fitted}
            bottom = max((p.row + p.h for p in fitted), default=1)
            surface._grid.rows = max(surface._grid.rows, min(96, bottom + 2))
            surface.relayout_for_width(width)
            after = {p.id: (p.col, p.row, p.w, p.h) for p in fitted}
            if after != before and surface._on_changed is not None:
                surface._on_changed(list(fitted))
        finally:
            self._fitting = False


def _wire_nested_toggles(root: QWidget, slot: Callable[[bool], None]) -> None:
    if isinstance(root, CollapsibleSection):
        root.toggled.connect(slot)
    for child in root.findChildren(CollapsibleSection):
        child.toggled.connect(slot)


def _measure_chrome_size(chrome: ModuleChrome) -> tuple[int, int]:
    """Preferred width/height so labels and fields are not clipped."""
    chrome.setMinimumSize(0, 0)
    chrome.setMaximumSize(16777215, 16777215)
    body = chrome.body
    body.setMinimumSize(0, 0)
    body.setMaximumSize(16777215, 16777215)
    # Wide but short: avoid inflated hints from a tall unconstrained parent.
    chrome.resize(900, 100)
    for section in body.findChildren(CollapsibleSection):
        section.updateGeometry()
    body.adjustSize()
    chrome.updateGeometry()
    chrome.adjustSize()
    lay = chrome.layout()
    if lay is not None:
        lay.activate()
        hint_w = lay.sizeHint().width()
        hint_h = lay.sizeHint().height()
    else:
        hint_w = chrome.sizeHint().width()
        hint_h = chrome.sizeHint().height()
    body_w = body.sizeHint().width()
    body_h = body.sizeHint().height() if body.isVisibleTo(chrome) else 0
    pad = 16
    width_px = max(160, hint_w, body_w + pad, chrome.minimumSizeHint().width())
    height_px = max(48, hint_h, body_h + 28, chrome.minimumSizeHint().height())
    return width_px, height_px
