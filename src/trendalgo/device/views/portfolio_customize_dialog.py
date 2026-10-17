"""Add/remove Dashboard modules for the active page (cross-page inventory)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.portfolio_grid_pack import pack_placements
from trendalgo.device.portfolio_layout_prefs import PageLayout, Placement
from trendalgo.device.portfolio_module_catalog import CATALOG, catalog_by_category
from trendalgo.device.views.widgets import section_title


class PortfolioCustomizeDialog(QDialog):
    def __init__(
        self,
        current: list[Placement],
        parent: QWidget | None = None,
        *,
        cols: int = 24,
        rows: int = 24,
        show_grid: bool = False,
        pages: list[PageLayout] | None = None,
        active_page_id: str = "",
        on_grid: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(S.PORTFOLIO_CUSTOMIZE)
        self.resize(480, 600)
        self._cols = cols
        self._on_grid = on_grid
        self._boxes: dict[str, QCheckBox] = {}
        self._present_here = {p.id for p in current}
        self._placed_on = _page_labels(pages or [], active_page_id)
        self._elsewhere = {
            mid for mid, label in self._placed_on.items() if mid not in self._present_here
        }
        host = QWidget()
        col = QVBoxLayout(host)
        grid_row = QHBoxLayout()
        self._cols_spin = QSpinBox()
        self._cols_spin.setRange(4, 32)
        self._cols_spin.setValue(cols)
        self._cols_spin.setPrefix(f"{S.PORTFOLIO_GRID_COLS} ")
        self._rows_spin = QSpinBox()
        self._rows_spin.setRange(4, 96)
        self._rows_spin.setValue(rows)
        self._rows_spin.setPrefix(f"{S.PORTFOLIO_GRID_ROWS} ")
        self._grid_btn = QPushButton(S.PORTFOLIO_SHOW_GRID)
        self._grid_btn.setCheckable(True)
        self._grid_btn.setChecked(show_grid)
        grid_row.addWidget(self._cols_spin)
        grid_row.addWidget(self._rows_spin)
        grid_row.addWidget(self._grid_btn)
        col.addLayout(grid_row)
        hint = QLabel(S.SETTINGS_CUSTOMIZE_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        col.addWidget(hint)
        select_all = QPushButton("Select all modules")
        select_all.clicked.connect(lambda _c=False: self._set_all(True))
        clear_all = QPushButton("Clear all")
        clear_all.clicked.connect(lambda _c=False: self._set_all(False))
        col.addWidget(select_all)
        col.addWidget(clear_all)
        for category, specs in catalog_by_category():
            col.addWidget(section_title(category))
            for spec in specs:
                label = spec.title
                elsewhere = self._placed_on.get(spec.id)
                if elsewhere and spec.id not in self._present_here:
                    label = f"{spec.title} — {elsewhere}"
                box = QCheckBox(label)
                box.setChecked(spec.id in self._present_here or spec.id in self._elsewhere)
                self._boxes[spec.id] = box
                col.addWidget(box)
        col.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(host)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)

    def _set_all(self, checked: bool) -> None:
        for mid, box in self._boxes.items():
            if mid in self._elsewhere and mid not in self._present_here:
                continue
            box.setChecked(checked)

    def selected_placements(self, existing: list[Placement]) -> list[Placement]:
        wanted: list[str] = []
        for spec in CATALOG:
            box = self._boxes[spec.id]
            if not box.isChecked():
                continue
            if spec.id in self._present_here or spec.id not in self._elsewhere:
                wanted.append(spec.id)
        return pack_placements(wanted, existing=existing, cols=self._cols_spin.value())

    def removed_from_other_pages(self) -> set[str]:
        """Module ids unchecked that lived only on other pages (or anywhere unchecked)."""
        return {mid for mid, box in self._boxes.items() if not box.isChecked()}

    def grid_settings(self) -> tuple[int, int, bool]:
        return self._cols_spin.value(), self._rows_spin.value(), self._grid_btn.isChecked()


def _page_labels(pages: list[PageLayout], active_page_id: str) -> dict[str, str]:
    """Map module id → page name for modules placed on any page."""
    out: dict[str, str] = {}
    for page in pages:
        for placement in page.placements:
            if placement.id in out and page.id != active_page_id:
                continue
            out[placement.id] = page.name
    return out
