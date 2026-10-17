"""Device app entry: take the profile lock, switch the device's own databases to WAL, open the window.

PySide6 is imported inside `run` so the logic modules and their tests never need Qt.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext, open_context
from trendalgo.device.db import enable_wal
from trendalgo.device.lock import ProfileBusyError, ProfileLock
from trendalgo.device.workers import WorkerPool

DEVICE_DATABASES = ("scanner", "bots", "journal")


def run(root: Path | None = None) -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

    from trendalgo.device.appearance import apply_saved_appearance, follow_color_scheme
    from trendalgo.device.icons import set_windows_app_id, splash_pixmap, window_icon
    from trendalgo.device.theme import apply_theme
    from trendalgo.device.views.main_window import MainWindow

    # Before QApplication: taskbar grouping uses the app icon, not python.exe.
    set_windows_app_id()
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    app.setApplicationName(S.APP_TITLE)
    app.setOrganizationName("TrendAlgo")
    icon = window_icon()
    app.setWindowIcon(icon)
    apply_theme(app)
    splash: QSplashScreen | None = None
    art = splash_pixmap()
    if art is not None and not art.isNull():
        splash = QSplashScreen(
            art.scaled(
                640,
                360,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        splash.show()
        app.processEvents()
    try:
        ctx = open_context(root)
    except OSError as exc:
        reason = exc.strerror or str(exc)
        if splash is not None:
            splash.close()
        QMessageBox.critical(None, S.APP_TITLE, S.PROFILE_FOLDER_FAILED.format(reason=reason))
        return 1
    apply_saved_appearance(app, ctx)
    follow_color_scheme(app, ctx)
    from trendalgo.device.crash_capture.install_handler import install_crash_handler
    from trendalgo.device.crash_capture.save_crashes import get_save_crashes
    from trendalgo.device.views.crash_review_dialog import offer_crash_review

    install_crash_handler(ctx.root, lambda: get_save_crashes(ctx.root))
    lock = ProfileLock(ctx.lock_path)
    try:
        lock.acquire()
    except ProfileBusyError as exc:
        if splash is not None:
            splash.close()
        QMessageBox.critical(None, S.APP_TITLE, str(exc))
        return 1
    pool = WorkerPool()
    try:
        window = MainWindow(
            ctx,
            pool,
            prepare_databases(ctx),
            on_setup_wizard=lambda: open_setup_wizard(ctx, lock),
        )
        window.show()
        if splash is not None:
            splash.finish(window)
        offer_crash_review(ctx, window)
        _offer_startup_extras(ctx, window)
        return app.exec()
    finally:
        pool.shutdown()
        lock.release()


def _offer_startup_extras(ctx: DeviceContext, window: object) -> None:
    """Crash review siblings: update/donate prompt and Feedback deep link (≤10 lines each)."""
    from PySide6.QtWidgets import QWidget

    from trendalgo import __version__ as _ver
    from trendalgo.device.about.run_updates import decide_launch_prompt
    from trendalgo.device.deep_link import feedback_link_from_argv
    from trendalgo.device.views.feedback_dialog import open_feedback
    from trendalgo.device.views.launch_prompt_dialog import offer_launch_prompt
    from trendalgo.device.views.main_window import SETTINGS, MainWindow

    parent = window if isinstance(window, QWidget) else None
    prompt = decide_launch_prompt(ctx.root, current_version=_ver)
    if prompt is not None:
        offer_launch_prompt(ctx, prompt, current_version=_ver, parent=parent)
    link = feedback_link_from_argv(sys.argv)
    if link is not None:
        if isinstance(window, MainWindow):
            window.show_page(SETTINGS)
        kind = "feature" if link.kind == "feature" else "bug"
        open_feedback(ctx, kind, parent=parent, description=link.subject)


def open_setup_wizard(ctx: DeviceContext, lock: ProfileLock) -> None:
    """Open the setup wizard from Settings. The window already holds the profile lock, so the
    wizard reuses it instead of asking for a second one."""
    from PySide6.QtWidgets import QMessageBox

    from trendalgo.device.wizard.credentials import CredentialError, open_store
    from trendalgo.device.wizard.view import WizardDialog

    try:
        store = open_store()
    except CredentialError as exc:
        QMessageBox.critical(None, S.APP_TITLE, str(exc))
        return
    WizardDialog(ctx, lock, store).exec()


def prepare_databases(ctx: DeviceContext) -> list[str]:
    """Switch the databases this device owns to WAL (D3). Shared API files stay as they are.
    Returns one notice per failure."""
    notices: list[str] = []
    for name in DEVICE_DATABASES:
        if name in ctx.shared:
            continue
        path = ctx.databases[name]
        if not path.is_file():
            continue
        try:
            enable_wal(path)
        except sqlite3.Error:
            notices.append(S.WAL_NOTICE.format(name=path.name))
    return notices
