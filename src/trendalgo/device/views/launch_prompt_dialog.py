"""Optional launch note: donate nudge or Download and install | Later."""

from __future__ import annotations

import webbrowser
from time import time

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
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
    dialog.setWindowTitle(S.ABOUT_UPDATE_TITLE)
    dialog.setMinimumWidth(420)
    body = QLabel()
    body.setWordWrap(True)
    buttons = QDialogButtonBox()
    layout = QVBoxLayout(dialog)
    layout.addWidget(body)
    if prompt.kind == "donate":
        body.setText(S.ABOUT_DONATE_PROMPT)
        donate = buttons.addButton(S.ABOUT_DONATE_ACCEPT, QDialogButtonBox.ButtonRole.AcceptRole)
        later = buttons.addButton(S.ABOUT_DONATE_LATER, QDialogButtonBox.ButtonRole.RejectRole)
        donate.clicked.connect(dialog.accept)
        later.clicked.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            webbrowser.open(primary_donate_url(load_donations()), new=2)
        mark_version_seen(ctx.root, current_version)
        return
    body.setText(S.ABOUT_UPDATE_BODY.format(version=prompt.version))
    if prompt.changelog:
        notes = QLabel(prompt.changelog)
        notes.setWordWrap(True)
        notes.setObjectName("hint")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(notes)
        scroll.setMaximumHeight(220)
        layout.addWidget(scroll)
    install = buttons.addButton(S.ABOUT_UPDATE_DOWNLOAD, QDialogButtonBox.ButtonRole.AcceptRole)
    later = buttons.addButton(S.ABOUT_UPDATE_LATER, QDialogButtonBox.ButtonRole.RejectRole)
    install.clicked.connect(dialog.accept)
    later.clicked.connect(dialog.reject)
    layout.addWidget(buttons)
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted and prompt.url.startswith("https://"):
        webbrowser.open(prompt.url, new=2)
    else:
        mark_update_checked(ctx.root, time() * 1000, dismissed_version=prompt.version)
