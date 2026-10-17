"""Settings section: per-module minimum grid size overrides."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.portfolio_layout_prefs import load_prefs, save_prefs
from trendalgo.device.portfolio_module_catalog import catalog_by_category, spec_for
from trendalgo.device.views.collapsible_section import CollapsibleSection


class DashboardModulesSection(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        *,
        on_saved: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._on_saved = on_saved
        self._spins: dict[str, tuple[QSpinBox, QSpinBox]] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        help_lbl = QLabel(S.SETTINGS_DASHBOARD_MODULES_HELP)
        help_lbl.setObjectName("hint")
        help_lbl.setWordWrap(True)
        layout.addWidget(help_lbl)
        for category, specs in catalog_by_category():
            group = CollapsibleSection(category, expanded=False, nested=True)
            for spec in specs:
                row = QHBoxLayout()
                label = QLabel(spec.title)
                label.setMinimumWidth(160)
                w_spin = QSpinBox()
                w_spin.setRange(1, spec.max_w)
                w_spin.setPrefix("W ")
                h_spin = QSpinBox()
                h_spin.setRange(1, spec.max_h)
                h_spin.setPrefix("H ")
                row.addWidget(label, 1)
                row.addWidget(w_spin)
                row.addWidget(h_spin)
                wrap = QWidget()
                wrap.setLayout(row)
                group.add_widget(wrap)
                self._spins[spec.id] = (w_spin, h_spin)
            layout.addWidget(group)
        reset = QPushButton(S.SETTINGS_DASHBOARD_RESET_MINS)
        reset.clicked.connect(lambda _c=False: self._reset_defaults())
        save = QPushButton(S.SETTINGS_DASHBOARD_SAVE_MINS)
        save.clicked.connect(lambda _c=False: self.save())
        layout.addWidget(reset)
        layout.addWidget(save)
        self._status = QLabel()
        self._status.setObjectName("hint")
        layout.addWidget(self._status)
        self.reload()

    def reload(self) -> None:
        prefs = load_prefs(self._ctx.root)
        for mid, (w_spin, h_spin) in self._spins.items():
            spec = spec_for(mid)
            if spec is None:
                continue
            if mid in prefs.module_mins:
                min_w, min_h = prefs.module_mins[mid]
            else:
                min_w, min_h = spec.min_w, spec.min_h
            w_spin.setValue(min_w)
            h_spin.setValue(min_h)

    def save(self) -> None:
        prefs = load_prefs(self._ctx.root)
        overrides: dict[str, tuple[int, int]] = {}
        for mid, (w_spin, h_spin) in self._spins.items():
            spec = spec_for(mid)
            if spec is None:
                continue
            min_w, min_h = w_spin.value(), h_spin.value()
            if min_w != spec.min_w or min_h != spec.min_h:
                overrides[mid] = (min_w, min_h)
        prefs.module_mins = overrides
        save_prefs(self._ctx.root, prefs)
        self._status.setText(S.SETTINGS_DASHBOARD_MINS_SAVED)
        if self._on_saved is not None:
            self._on_saved()

    def _reset_defaults(self) -> None:
        for mid, (w_spin, h_spin) in self._spins.items():
            spec = spec_for(mid)
            if spec is None:
                continue
            w_spin.setValue(spec.min_w)
            h_spin.setValue(spec.min_h)
        self.save()
