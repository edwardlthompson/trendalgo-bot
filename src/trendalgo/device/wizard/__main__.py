"""Open the setup wizard: `python -m trendalgo.device.wizard`. It holds the profile lock while open (D3).

PySide6 and the vault are imported inside `run`, so importing this module loads no window.
"""

from __future__ import annotations

import sys
from pathlib import Path

from trendalgo.device import strings as S
from trendalgo.device.context import open_context
from trendalgo.device.lock import ProfileBusyError, ProfileLock
from trendalgo.device.wizard import strings as W


def run(root: Path | None = None) -> int:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from trendalgo.device.appearance import apply_saved_appearance
    from trendalgo.device.icons import window_icon
    from trendalgo.device.theme import apply_theme
    from trendalgo.device.wizard.credentials import CredentialError, open_store
    from trendalgo.device.wizard.view import WizardDialog

    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    app.setWindowIcon(window_icon())
    apply_theme(app)
    try:
        ctx = open_context(root)
    except OSError as exc:
        reason = exc.strerror or str(exc)
        QMessageBox.critical(None, W.APP_TITLE, S.PROFILE_FOLDER_FAILED.format(reason=reason))
        return 1
    apply_saved_appearance(app, ctx)
    lock = ProfileLock(ctx.lock_path)
    try:
        lock.acquire()
    except ProfileBusyError as exc:
        QMessageBox.critical(None, W.APP_TITLE, str(exc))
        return 1
    try:
        store = open_store()
    except CredentialError as exc:
        QMessageBox.critical(None, W.APP_TITLE, str(exc))
        lock.release()
        return 1
    try:
        WizardDialog(ctx, lock, store).exec()
    finally:
        lock.release()
    return 0


if __name__ == "__main__":
    sys.exit(run())
