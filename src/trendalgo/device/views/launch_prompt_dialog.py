"""Optional launch note: donate nudge or Install | Later. Never blocks startup hard."""

from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from trendalgo.device.about.donations import load_donations, primary_donate_url
from trendalgo.device.about.run_updates import LaunchPrompt
from trendalgo.device.about.update_prefs import mark_update_checked, mark_version_seen
from trendalgo.device.context import DeviceContext


def offer_launch_prompt(
    ctx: DeviceContext,
    prompt: LaunchPrompt,
    *,
    current_version: str,
    parent: QWidget | None = None,
) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle("TrendAlgo")
    body = QLabel()
    body.setWordWrap(True)
    buttons = QDialogButtonBox()
    layout = QVBoxLayout(dialog)
    layout.addWidget(body)
    layout.addWidget(buttons)
    if prompt.kind == "donate":
        body.setText(
            "If TrendAlgo helps you, you can support the project. Optional — never required."
        )
        donate = buttons.addButton("Donate", QDialogButtonBox.ButtonRole.AcceptRole)
        later = buttons.addButton("Not now", QDialogButtonBox.ButtonRole.RejectRole)
        donate.clicked.connect(dialog.accept)
        later.clicked.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            webbrowser.open(primary_donate_url(load_donations()), new=2)
        mark_version_seen(ctx.root, current_version)
        return
    body.setText(f"A newer installer ({prompt.version}) is available.")
    install = buttons.addButton("Install", QDialogButtonBox.ButtonRole.AcceptRole)
    later = buttons.addButton("Later", QDialogButtonBox.ButtonRole.RejectRole)
    install.clicked.connect(dialog.accept)
    later.clicked.connect(dialog.reject)
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted and prompt.url.startswith("https://"):
        webbrowser.open(prompt.url, new=2)
    else:
        from time import time

        mark_update_checked(ctx.root, time() * 1000, dismissed_version=prompt.version)
