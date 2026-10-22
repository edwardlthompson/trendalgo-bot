"""Main window: tabs first, More overflow, one page at a time."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QMenu,
    QScrollArea,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import nav_layout as _nav
from trendalgo.device import strings as S
from trendalgo.device.autostart import is_enabled as autostart_is_enabled
from trendalgo.device.autostart import set_enabled as set_autostart
from trendalgo.device.context import DeviceContext
from trendalgo.device.flow_layout import FlowLayout
from trendalgo.device.icons import nav_icon, window_icon
from trendalgo.device.nav_layout import NAV_CATALOG, SCANNER, NavItem, pack_nav
from trendalgo.device.notify_prefs import load_prefs
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.ui_state import default_nav_page, save_nav_page
from trendalgo.device.views.alerts_page import AlertsPage
from trendalgo.device.views.backtest_page import BacktestPage
from trendalgo.device.views.billing_page import BillingPage
from trendalgo.device.views.bots_page import BotsPage
from trendalgo.device.views.debug_page import DebugPage
from trendalgo.device.views.export_page import ExportPage
from trendalgo.device.views.glossary_page import GlossaryPage
from trendalgo.device.views.portfolio_page import PortfolioPage
from trendalgo.device.views.scanner_page import ScannerPage
from trendalgo.device.views.settings_page import SettingsPage
from trendalgo.device.views.tray_controller import TrayController, install_quit_on_last_window
from trendalgo.device.window_geometry import restore_window_geometry, save_window_geometry
from trendalgo.device.workers import WorkerPool

# Re-export page indices / legacy nav constants for tests and deep-links.
AI = _nav.AI
ALERTS = _nav.ALERTS
BACKTESTS = _nav.BACKTESTS
BILLING = _nav.BILLING
DEBUG = _nav.DEBUG
EXPORT = _nav.EXPORT
GLOSSARY = _nav.GLOSSARY
MORE_ITEMS = _nav.MORE_ITEMS
PLAN = _nav.PLAN  # alias of STATUS (Bots hub)
PORTFOLIO = _nav.PORTFOLIO
PRIMARY_COUNT = _nav.PRIMARY_COUNT
PRIMARY_GLYPHS = _nav.PRIMARY_GLYPHS
RESEARCH = _nav.RESEARCH
SETTINGS = _nav.SETTINGS
STATUS = _nav.STATUS
ICON_PX = 20


def _scrolled(page: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(page)
    return area


class MainWindow(QMainWindow):
    def __init__(
        self,
        ctx: DeviceContext,
        pool: WorkerPool,
        notices: list[str] | None = None,
        on_setup_wizard: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(S.APP_TITLE)
        self.setWindowIcon(window_icon())
        self.setMinimumSize(480, 360)
        self.resize(1100, 720)
        self._ctx = ctx
        self._tray: TrayController | None = None
        self._scanner_page: ScannerPage | None = None
        self._alerts_page: AlertsPage | None = None
        self._page_index = PORTFOLIO
        self._visible_items: list[NavItem] = list(NAV_CATALOG)
        self._badge = QLabel(S.BADGE_NO_HOST)
        self._badge.setObjectName("badge")
        self._badge.setAccessibleName(S.BADGE_NO_HOST)
        self._nav = QTabBar()
        self._nav.setAccessibleName(S.NAV_LABEL)
        self._nav.setDrawBase(False)
        self._nav.setExpanding(False)
        self._nav.setUsesScrollButtons(False)
        self._nav.setIconSize(QSize(ICON_PX, ICON_PX))
        self._more = QToolButton()
        self._more.setObjectName("navMore")
        self._more.setText(S.NAV_MORE)
        self._more.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._more.setAccessibleName(S.NAV_MORE)
        self._stack = QStackedWidget()
        bots_page = BotsPage(ctx, on_host_badge=self._set_host_badge)

        def open_bots_from_fleet(fields: dict[str, str]) -> None:
            bots_page.prefill_from_fleet(fields)
            self.show_page(STATUS)

        def create_bot_from_scanner(fields: dict[str, str], note: str) -> str:
            ok, msg = bots_page.add_bot_from_fields(fields)
            self.show_page(STATUS)
            bots_page.reload_performance()
            return msg if ok else (note or msg)

        alerts = AlertsPage(ctx.root, on_toast=self._toast)
        self._alerts_page = alerts
        scanner = ScannerPage(
            ctx,
            on_create_bot=create_bot_from_scanner,
            on_toast=self._toast,
            on_alerts_changed=alerts.reload,
        )
        self._scanner_page = scanner
        # Stack index == nav_layout page index: Portfolio, Alerts, Scanner, Backtest, Bots, …
        self._portfolio = PortfolioPage(ctx)
        for page in (
            self._portfolio,
            alerts,
            scanner,
            BacktestPage(ctx, pool, on_open_plan=open_bots_from_fleet),
            _scrolled(bots_page),
            GlossaryPage(),
            ExportPage(ctx),
            BillingPage(),
            _scrolled(
                SettingsPage(
                    ctx,
                    on_setup_wizard,
                    on_module_mins_saved=self._portfolio.reload_module_mins,
                )
            ),
            DebugPage(ctx),
        ):
            self._stack.addWidget(page)
        self._nav.currentChanged.connect(self._on_primary)
        self._menu = QMenu(self._more)
        self._more.setMenu(self._menu)
        self._more_actions: dict[int, QAction] = {}
        self._navbar = QWidget()
        self._navbar.setObjectName("navRow")
        nav_row = FlowLayout(self._navbar, margin=0, h_spacing=8, v_spacing=4)
        nav_row.addWidget(self._nav)
        nav_row.addWidget(self._more)
        nav_row.addWidget(self._badge)
        body = QWidget()
        column = QVBoxLayout(body)
        column.setContentsMargins(16, 12, 16, 16)
        column.setSpacing(12)
        column.addWidget(self._navbar)
        column.addWidget(self._stack, 1)
        self.setCentralWidget(body)
        notes = [S.PROFILE_NOTE.format(path=ctx.root), *(notices or [])]
        if {"scanner", "bots", "journal"} & ctx.shared:
            notes.append(S.DATA_NOTE.format(path=ctx.databases["scanner"].parent))
        self.statusBar().addWidget(QLabel("  ".join(notes)))
        if not restore_window_geometry(ctx.root, self):
            self.resize(1100, 720)
        self._rebuild_nav(force=True)
        self.show_page(default_nav_page(ctx.root))
        self._install_tray()
        self._ensure_default_autostart()
        QTimer.singleShot(0, lambda: self._rebuild_nav(force=True))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._rebuild_nav()

    def _catalog_widths(self) -> list[int]:
        probe = QTabBar()
        probe.setIconSize(QSize(ICON_PX, ICON_PX))
        color = colors_for(active_mode())["onSurfaceVariant"]
        for item in NAV_CATALOG:
            probe.addTab(nav_icon(item.glyph, color, ICON_PX), item.label)
        return [max(1, probe.tabSizeHint(i).width()) for i in range(probe.count())]

    def _rebuild_nav(self, *, force: bool = False) -> None:
        if not hasattr(self, "_navbar"):
            return
        badge_w = max(self._badge.sizeHint().width(), 48)
        available = max(0, self._navbar.width() - badge_w - 16)
        more_w = max(self._more.sizeHint().width(), 64)
        widths = self._catalog_widths()
        visible, overflow = pack_nav(
            NAV_CATALOG,
            available_width=available if available > 0 else 10_000,
            tab_widths=widths,
            more_width=more_w,
        )
        if not force and visible == self._visible_items:
            self._sync_nav_selection()
            return
        self._visible_items = visible
        self._nav.blockSignals(True)
        while self._nav.count():
            self._nav.removeTab(0)
        color = colors_for(active_mode())["onSurfaceVariant"]
        for item in visible:
            self._nav.addTab(nav_icon(item.glyph, color, ICON_PX), item.label)
        self._menu.clear()
        self._more_actions = {}
        for item in overflow:
            action = self._menu.addAction(item.label)
            action.setData(item.index)
            action.setIcon(nav_icon(item.glyph, color, ICON_PX))
            action.triggered.connect(lambda _c=False, i=item.index: self.show_page(i))
            self._more_actions[item.index] = action
        self._more.setVisible(bool(overflow))
        self._more.setIcon(nav_icon("more", color, ICON_PX))
        self._sync_nav_selection()
        self._nav.blockSignals(False)

    def _sync_nav_selection(self) -> None:
        for tab_i, item in enumerate(self._visible_items):
            if item.index == self._page_index:
                self._nav.setCurrentIndex(tab_i)
                return
        self._nav.setCurrentIndex(-1)

    def _install_tray(self) -> None:
        app = QApplication.instance()
        tray = TrayController(
            window=self,
            icon=window_icon(),
            on_show=self._show_from_tray,
            on_scanner=lambda: self._focus_scanner(),
            on_quit=self._quit_app,
            on_run_scan=self._run_scan_from_tray,
        )
        self._tray = tray
        if isinstance(app, QApplication):
            install_quit_on_last_window(app, tray_ok=tray.available)

    def _ensure_default_autostart(self) -> None:
        prefs = load_prefs(self._ctx.root)
        if prefs.start_with_windows and not autostart_is_enabled():
            set_autostart(True)

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _focus_scanner(self) -> None:
        self._show_from_tray()
        self.show_page(SCANNER)

    def _focus_alerts(self) -> None:
        self._show_from_tray()
        self.show_page(ALERTS)
        if self._alerts_page is not None:
            self._alerts_page.reload()

    def _run_scan_from_tray(self) -> None:
        self._focus_scanner()
        if self._scanner_page is not None:
            self._scanner_page.start_scan()

    def _set_host_badge(self, linked: bool, *, pending_events: int = 0) -> None:
        if not linked:
            text = S.BADGE_NO_HOST
        elif pending_events > 0:
            text = S.BADGE_HOST_EVENTS.format(count=pending_events)
        else:
            text = S.BADGE_HOST_LINKED
        self._badge.setText(text)
        self._badge.setAccessibleName(text)

    def _toast(self, title: str, body: str) -> None:
        if self._tray is not None:
            self._tray.show_message(title, body)

    def _quit_app(self) -> None:
        if self._scanner_page is not None:
            self._scanner_page.stop_autoscan()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        save_nav_page(self._ctx.root, self._page_index)
        save_window_geometry(self._ctx.root, self)
        if self._tray is not None and self._tray.available:
            event.ignore()
            self.hide()
            self._tray.show_message(S.APP_TITLE, S.TRAY_HIDDEN)
            return
        super().closeEvent(event)

    def show_page(self, index: int) -> None:
        self._page_index = index
        self._stack.setCurrentIndex(index)
        self._nav.blockSignals(True)
        self._sync_nav_selection()
        self._nav.blockSignals(False)
        save_nav_page(self._ctx.root, index)

    def _on_primary(self, tab_index: int) -> None:
        if 0 <= tab_index < len(self._visible_items):
            self.show_page(self._visible_items[tab_index].index)

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, "_nav"):
            self._rebuild_nav(force=True)
