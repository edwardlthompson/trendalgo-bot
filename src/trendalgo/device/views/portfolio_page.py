"""Dashboard page: modular snap-to-grid portfolio canvas."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_client import HostRefusedError
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.icons import nav_icon
from trendalgo.device.portfolio_demo import is_demo_source, seed_demo_portfolio
from trendalgo.device.portfolio_grid_pack import required_rows
from trendalgo.device.portfolio_layout_prefs import (
    LayoutPrefs,
    Placement,
    active_page,
    factory_defaults,
    load_prefs,
    save_prefs,
)
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.portfolio_share import (
    default_portfolio_export_path,
    share_module_png,
    share_widget_png,
)
from trendalgo.device.portfolio_sync import apply_host_portfolio
from trendalgo.device.stores import StoreReadError, read_portfolio
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.calendar_wizard import CalendarWizardDialog
from trendalgo.device.views.modules import bind_overview, build_module
from trendalgo.device.views.portfolio_customize_dialog import PortfolioCustomizeDialog
from trendalgo.device.views.portfolio_grid_canvas import GridCanvas
from trendalgo.device.views.widgets import (
    clear_problem,
    mark_primary,
    problem_label,
    show_problem,
)
from trendalgo.portfolio.db import PortfolioStore


class PortfolioPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._path: Path | None = ctx.portfolio_path
        self._as_of: str | None = None
        self._overview: PortfolioOverview | None = None
        self._demo_mode = False
        self._real_path: Path | None = ctx.portfolio_path
        self._prefs: LayoutPrefs = load_prefs(ctx.root)
        # Stamp current layout_version so factory Overview sticks after polish bumps.
        save_prefs(ctx.root, self._prefs)
        self._modules: dict[str, QWidget] = {}

        self._reload = QPushButton(S.RELOAD)
        self._reload.clicked.connect(lambda _c=False: self.reload())
        self._sync = mark_primary(QPushButton(S.PORTFOLIO_SYNC_ALL))
        self._sync.clicked.connect(lambda _c=False: self._sync_from_host())
        self._customize = QPushButton(S.PORTFOLIO_CUSTOMIZE)
        self._customize.clicked.connect(lambda _c=False: self._open_customize())
        self._export_page = QToolButton()
        self._export_page.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._export_page.setIcon(
            nav_icon("share", colors_for(active_mode())["onSurfaceVariant"], 16)
        )
        self._export_page.setIconSize(QSize(16, 16))
        self._export_page.setObjectName("dashShareBtn")
        self._export_page.setToolTip(S.PORTFOLIO_SHARE_TIP)
        self._export_page.setAccessibleName(S.PORTFOLIO_EXPORT_PAGE)
        self._export_page.clicked.connect(lambda _c=False: self._export_page_png())
        self._demo_btn = QPushButton(S.PORTFOLIO_LOAD_DEMO)
        self._demo_btn.setToolTip(S.PORTFOLIO_DEMO_TIP)
        self._demo_btn.clicked.connect(lambda _c=False: self._toggle_demo())
        self._export_csv = QPushButton(S.PORTFOLIO_EXPORT_CSV)
        self._export_csv.clicked.connect(lambda _c=False: self._export_csv_file())
        self._cal_wizard = QPushButton(S.PORTFOLIO_CALENDAR_SETUP)
        self._cal_wizard.clicked.connect(lambda _c=False: self._open_calendar_wizard())
        self._demo = QLabel(S.PORTFOLIO_DEMO_BADGE)
        self._demo.setObjectName("badge")
        self._demo.hide()
        self._cols = QSpinBox()
        self._cols.setRange(4, 32)
        self._cols.setValue(self._prefs.grid.cols)
        self._cols.setPrefix(f"{S.PORTFOLIO_GRID_COLS} ")
        self._cols.valueChanged.connect(self._grid_changed)
        self._rows = QSpinBox()
        self._rows.setRange(4, 96)
        self._rows.setValue(self._prefs.grid.rows)
        self._rows.setPrefix(f"{S.PORTFOLIO_GRID_ROWS} ")
        self._rows.valueChanged.connect(self._grid_changed)
        self._show_grid = QPushButton(S.PORTFOLIO_SHOW_GRID)
        self._show_grid.setCheckable(True)
        self._show_grid.setChecked(self._prefs.grid.show_grid)
        self._show_grid.toggled.connect(self._toggle_grid)
        self._problem = problem_label()
        self._caption = QLabel()
        self._caption.setObjectName("hint")
        self._caption.setWordWrap(True)
        self._tabs = QTabBar()
        self._tabs.setExpanding(False)
        self._tabs.setDrawBase(False)
        self._tabs.currentChanged.connect(self._on_page_tab)
        self._add_page_btn = QPushButton(S.PORTFOLIO_ADD_PAGE)
        self._add_page_btn.clicked.connect(lambda _c=False: self._add_page())
        self._canvas = GridCanvas(
            on_placements_changed=self._placements_changed,
            on_export_module=self._export_module,
            on_remove_module=self._remove_module,
        )
        # Secondary tools live under Customize; keep the chrome CoinStats-quiet.
        self._cols.hide()
        self._rows.hide()
        self._show_grid.hide()
        self._export_csv.hide()
        self._cal_wizard.hide()
        self._edit_layout = QPushButton(S.PORTFOLIO_EDIT_LAYOUT)
        self._edit_layout.setCheckable(True)
        self._edit_layout.toggled.connect(self._toggle_edit_layout)
        self._demo_btn.hide()
        self._reload.hide()
        # No page title/subtitle — nav already says Dashboard; Total Worth lives in modules.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        for w in (
            self._sync,
            self._customize,
            self._edit_layout,
            self._export_page,
            self._demo,
            self._demo_btn,
            self._reload,
        ):
            actions.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
        actions.addStretch(1)
        layout.addLayout(actions)
        pages_row = QHBoxLayout()
        pages_row.setSpacing(4)
        pages_row.addWidget(self._tabs, 1)
        pages_row.addWidget(self._add_page_btn)
        self._add_page_btn.hide()
        layout.addLayout(pages_row)
        layout.addWidget(self._problem)
        self._caption.hide()
        layout.addWidget(self._caption)
        layout.addWidget(self._canvas, 1)
        self._rebuild_tabs()
        self._rebuild_canvas()
        self.reload()

    def _toggle_edit_layout(self, checked: bool) -> None:
        self._canvas.set_edit_mode(checked)
        self._add_page_btn.setVisible(checked)
        self._demo_btn.setVisible(checked)
        self._reload.setVisible(checked)
        self._export_page.setVisible(True)

    def reload(self) -> None:
        if self._demo_mode:
            path = self._path if self._path is not None else (self._ctx.root / "portfolio-demo.db")
            if not path.is_file():
                seed_demo_portfolio(path)
        else:
            candidate = self._path or self._ctx.portfolio_path
            if candidate is None or not candidate.is_file():
                path = self._ctx.root / "portfolio-demo.db"
                seed_demo_portfolio(path)
                self._demo_mode = True
                self._demo_btn.setText(S.PORTFOLIO_EXIT_DEMO)
                self._path = path
            else:
                path = candidate
        try:
            overview = read_portfolio(path, as_of_date=self._as_of)
        except StoreReadError as exc:
            show_problem(self._problem, str(exc))
            return
        clear_problem(self._problem)
        if overview is None and self._demo_mode:
            seed_demo_portfolio(path)
            overview = read_portfolio(path, as_of_date=self._as_of)
        if overview is None:
            show_problem(self._problem, S.PORTFOLIO_EMPTY_BODY)
            return
        self._path = path
        self._apply_overview(overview)

    def _apply_overview(self, overview: PortfolioOverview) -> None:
        self._overview = overview
        demo = self._demo_mode or is_demo_source(overview.source)
        self._demo.setVisible(demo)
        self._demo_btn.setText(S.PORTFOLIO_EXIT_DEMO if demo else S.PORTFOLIO_LOAD_DEMO)
        if demo:
            self._demo_mode = True
        self._caption.hide()
        for module in self._modules.values():
            bind_overview(module, overview, range_key=self._prefs.range)

    def _rebuild_tabs(self) -> None:
        self._tabs.blockSignals(True)
        while self._tabs.count() > 0:
            self._tabs.removeTab(0)
        active = 0
        for i, page in enumerate(self._prefs.pages):
            self._tabs.addTab(page.name)
            if page.id == self._prefs.active_page_id:
                active = i
        self._tabs.setCurrentIndex(active)
        self._tabs.blockSignals(False)

    def _rebuild_canvas(self) -> None:
        page = active_page(self._prefs)
        self._modules = {}
        bodies: dict[str, QWidget] = {}
        for placement in page.placements:
            body = build_module(
                placement.id,
                self._ctx,
                on_range=self._on_range,
                on_calendar_setup=self._open_calendar_wizard,
            )
            self._modules[placement.id] = body
            bodies[placement.id] = body
        self._canvas.set_grid(self._prefs.grid)
        self._canvas.set_module_mins(self._prefs.module_mins)
        self._canvas.set_modules(list(page.placements), bodies)
        if self._overview is not None:
            self._apply_overview(self._overview)

    def reload_module_mins(self) -> None:
        """Pull Settings overrides from disk into the live canvas (do not rebuild widgets)."""
        disk = load_prefs(self._ctx.root)
        self._prefs.module_mins = dict(disk.module_mins)
        self._canvas.set_module_mins(self._prefs.module_mins)

    def showEvent(self, event: object) -> None:  # noqa: N802
        super().showEvent(event)  # type: ignore[misc]
        self.reload_module_mins()

    def _persist(self) -> None:
        # Preserve Settings module_mins — this page's in-memory copy can be stale.
        disk = load_prefs(self._ctx.root)
        self._prefs.module_mins = dict(disk.module_mins)
        save_prefs(self._ctx.root, self._prefs)
        self._canvas.set_module_mins(self._prefs.module_mins)

    def _on_page_tab(self, index: int) -> None:
        if index < 0 or index >= len(self._prefs.pages):
            return
        self._prefs.active_page_id = self._prefs.pages[index].id
        self._persist()
        self._rebuild_canvas()

    def _add_page(self) -> None:
        n = len(self._prefs.pages) + 1
        page_id = f"page-{n}"
        from trendalgo.device.portfolio_layout_prefs import PageLayout

        self._prefs.pages.append(PageLayout(id=page_id, name=f"Page {n}", placements=[]))
        self._prefs.active_page_id = page_id
        self._persist()
        self._rebuild_tabs()
        self._rebuild_canvas()

    def _grid_changed(self, _value: int = 0) -> None:
        self._prefs.grid.cols = self._cols.value()
        self._prefs.grid.rows = self._rows.value()
        self._persist()
        self._canvas.set_grid(self._prefs.grid)

    def _toggle_grid(self, checked: bool) -> None:
        self._prefs.grid.show_grid = checked
        self._persist()
        self._canvas.set_grid(self._prefs.grid)

    def _on_range(self, key: str) -> None:
        self._prefs.range = key or "1y"
        self._persist()
        if self._overview is not None:
            self._apply_overview(self._overview)

    def _placements_changed(self, placements: list[Placement]) -> None:
        page = active_page(self._prefs)
        page.placements = placements
        self._persist()

    def _remove_module(self, module_id: str) -> None:
        page = active_page(self._prefs)
        page.placements = [p for p in page.placements if p.id != module_id]
        self._persist()
        self._rebuild_canvas()

    def _open_customize(self) -> None:
        page = active_page(self._prefs)
        dialog = PortfolioCustomizeDialog(
            page.placements,
            self,
            cols=self._prefs.grid.cols,
            rows=self._prefs.grid.rows,
            show_grid=self._prefs.grid.show_grid,
            pages=self._prefs.pages,
            active_page_id=page.id,
        )
        if dialog.exec():
            cols, rows, show_grid = dialog.grid_settings()
            self._prefs.grid.cols = cols
            self._prefs.grid.rows = rows
            self._prefs.grid.show_grid = show_grid
            self._cols.setValue(cols)
            self._rows.setValue(rows)
            self._show_grid.setChecked(show_grid)
            page.placements = dialog.selected_placements(page.placements)
            removed = dialog.removed_from_other_pages()
            if removed:
                for other in self._prefs.pages:
                    other.placements = [p for p in other.placements if p.id not in removed]
            needed = required_rows(page.placements, minimum=self._prefs.grid.rows)
            if needed > self._prefs.grid.rows:
                self._prefs.grid.rows = min(96, needed)
                self._rows.setValue(self._prefs.grid.rows)
            self._persist()
            self._rebuild_canvas()

    def _open_calendar_wizard(self) -> None:
        CalendarWizardDialog(self).exec()
        self._rebuild_canvas()

    def _export_module(self, module_id: str, widget: QWidget) -> None:
        suggested = str(default_portfolio_export_path(self._ctx.root, label=f"mod-{module_id}"))
        chosen, _flt = QFileDialog.getSaveFileName(
            self,
            S.PORTFOLIO_EXPORT_MODULE,
            suggested,
            S.SCANNER_SHARE_FILTER,
        )
        if not chosen:
            return
        try:
            out = share_module_png(widget, self._ctx.root, module_id=module_id, dest=Path(chosen))
        except OSError as exc:
            show_problem(self._problem, str(exc))
            QMessageBox.warning(self, S.PORTFOLIO_EXPORT_MODULE, str(exc))
            return
        clear_problem(self._problem)
        self._show_share_done(out)

    def _export_page_png(self, dest: Path | None = None) -> None:
        page = active_page(self._prefs)
        if dest is None:
            suggested = str(default_portfolio_export_path(self._ctx.root, label=f"page-{page.id}"))
            chosen, _flt = QFileDialog.getSaveFileName(
                self,
                S.PORTFOLIO_EXPORT_PAGE,
                suggested,
                S.SCANNER_SHARE_FILTER,
            )
            if not chosen:
                return
            dest = Path(chosen)
        try:
            # Capture the live canvas (layout + chrome), not raw module bodies.
            out = share_widget_png(
                self._canvas.surface(),
                self._ctx.root,
                tab=f"page-{page.id}",
                dest=dest,
            )
        except OSError as exc:
            show_problem(self._problem, str(exc))
            QMessageBox.warning(self, S.PORTFOLIO_EXPORT_PAGE, str(exc))
            return
        clear_problem(self._problem)
        self._show_share_done(out)

    def _show_share_done(self, out: Path) -> None:
        msg = S.PORTFOLIO_SHARE_DONE.format(name=out.name, path=str(out.parent))
        self._caption.setText(msg)
        self._caption.show()
        QMessageBox.information(self, S.PORTFOLIO_EXPORT_PAGE, msg)

    def _toggle_demo(self) -> None:
        if self._demo_mode:
            self._demo_mode = False
            self._path = self._real_path
            self._demo_btn.setText(S.PORTFOLIO_LOAD_DEMO)
            self.reload()
            return
        demo_path = self._ctx.root / "portfolio-demo.db"
        seed_demo_portfolio(demo_path)
        if self._path is not None and self._path.resolve() != demo_path.resolve():
            self._real_path = self._path
        elif self._ctx.portfolio_path is not None:
            self._real_path = self._ctx.portfolio_path
        self._demo_mode = True
        self._path = demo_path
        self._demo_btn.setText(S.PORTFOLIO_EXIT_DEMO)
        self._as_of = None
        self.reload()

    def _sync_from_host(self) -> None:
        client = try_open_host_client(self._ctx.settings_path)
        if client is None:
            show_problem(self._problem, S.PORTFOLIO_SYNC_NO_HOST)
            return
        try:
            response = client.get_portfolio()
        except HostRefusedError as exc:
            show_problem(self._problem, exc.problem.message)
            return
        if response.status == 0:
            show_problem(self._problem, S.PORTFOLIO_SYNC_UNREACHABLE)
            return
        if not response.ok:
            show_problem(self._problem, S.PORTFOLIO_SYNC_REFUSED)
            return
        data = response.data or {}
        if not data.get("snapshot"):
            show_problem(self._problem, S.PORTFOLIO_SYNC_EMPTY)
            return
        dest = self._real_path or self._ctx.portfolio_path or (self._ctx.root / "portfolio.db")
        if apply_host_portfolio(Path(dest), data):
            self._demo_mode = False
            self._real_path = Path(dest)
            self._path = Path(dest)
            self._demo_btn.setText(S.PORTFOLIO_LOAD_DEMO)
            clear_problem(self._problem)
            self._caption.setText(S.PORTFOLIO_SYNC_APPLIED)
            self.reload()
            return
        show_problem(self._problem, S.PORTFOLIO_SYNC_EMPTY)

    def _export_csv_file(self) -> None:
        path = self._path
        if path is None or not path.is_file():
            show_problem(self._problem, S.PORTFOLIO_EMPTY_BODY)
            return
        try:
            store = PortfolioStore(path, create=False)
            accounts = store.list_accounts()
            if not accounts:
                show_problem(self._problem, S.PORTFOLIO_EMPTY_BODY)
                return
            csv_text = store.export_holdings_csv(int(accounts[0]["id"]))
            out = self._ctx.root / "exports" / "portfolio-holdings.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(csv_text, encoding="utf-8")
            clear_problem(self._problem)
            self._caption.setText(S.EXPORT_DONE.format(name=out.name, path=out))
        except Exception as exc:
            show_problem(self._problem, str(exc))

    def reset_layout(self) -> None:
        self._prefs = factory_defaults()
        self._persist()
        self._cols.setValue(self._prefs.grid.cols)
        self._rows.setValue(self._prefs.grid.rows)
        self._rebuild_tabs()
        self._rebuild_canvas()
