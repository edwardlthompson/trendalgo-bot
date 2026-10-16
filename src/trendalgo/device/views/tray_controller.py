"""System tray: keep app alive, confirm quit (scanning stops)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget

from trendalgo.device import strings as S


class TrayController:
    def __init__(
        self,
        *,
        window: QWidget,
        icon: QIcon,
        on_show: Callable[[], None],
        on_scanner: Callable[[], None],
        on_quit: Callable[[], None],
        on_run_scan: Callable[[], None] | None = None,
    ) -> None:
        self._window = window
        self._on_quit = on_quit
        self._tray = QSystemTrayIcon(icon, window)
        self._tray.setToolTip(S.APP_TITLE)
        menu = QMenu()
        show = QAction(S.TRAY_SHOW, menu)
        show.triggered.connect(lambda _c=False: on_show())
        scanner = QAction(S.TRAY_SCANNER, menu)
        scanner.triggered.connect(lambda _c=False: on_scanner())
        menu.addAction(show)
        menu.addAction(scanner)
        if on_run_scan is not None:
            run = QAction(S.SCAN_RUN, menu)
            run.triggered.connect(lambda _c=False: on_run_scan())
            menu.addAction(run)
        quit_act = QAction(S.TRAY_QUIT, menu)
        quit_act.triggered.connect(lambda _c=False: self.request_quit())
        menu.addSeparator()
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._available = QSystemTrayIcon.isSystemTrayAvailable()
        if self._available:
            self._tray.show()

    @property
    def available(self) -> bool:
        return self._available

    def show_message(self, title: str, body: str) -> None:
        if self._available:
            self._tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 8000)

    def request_quit(self) -> None:
        answer = QMessageBox.question(
            self._window,
            S.TRAY_QUIT_TITLE,
            S.TRAY_QUIT_BODY,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._on_quit()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()


def install_quit_on_last_window(app: QApplication, *, tray_ok: bool) -> None:
    app.setQuitOnLastWindowClosed(not tray_ok)
