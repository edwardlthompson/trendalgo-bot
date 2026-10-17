"""One review dialog for a pending local crash. Never opens GitHub or sends."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device.context import DeviceContext
from trendalgo.device.crash_capture import copy as C
from trendalgo.device.crash_capture.pending_crash import clear_pending_crash, read_pending_crash


def offer_crash_review(ctx: DeviceContext, parent: QWidget | None = None) -> None:
    pending = read_pending_crash(ctx.root)
    if pending is None:
        return
    dialog = QDialog(parent)
    dialog.setWindowTitle(C.REVIEW_TITLE)
    body = QLabel(C.REVIEW_BODY)
    body.setWordWrap(True)
    message = QPlainTextEdit()
    message.setReadOnly(True)
    message.setPlainText(
        f"{C.REVIEW_MESSAGE}:\n{pending.message}\n\n{C.REVIEW_STACK}:\n{pending.stack}"
    )
    message.setMinimumHeight(180)
    buttons = QDialogButtonBox()
    clear_btn = buttons.addButton(C.REVIEW_CLEAR, QDialogButtonBox.ButtonRole.AcceptRole)
    keep_btn = buttons.addButton(C.REVIEW_KEEP, QDialogButtonBox.ButtonRole.RejectRole)
    layout = QVBoxLayout(dialog)
    layout.addWidget(body)
    layout.addWidget(message)
    layout.addWidget(buttons)
    clear_btn.clicked.connect(dialog.accept)
    keep_btn.clicked.connect(dialog.reject)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        clear_pending_crash(ctx.root)
