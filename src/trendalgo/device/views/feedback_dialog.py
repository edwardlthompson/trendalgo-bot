"""About feedback review dialog: preview, Copy, Open GitHub (when ready), Discard."""

from __future__ import annotations

import platform
import webbrowser
from typing import Literal

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from trendalgo import __version__
from trendalgo.device.context import DeviceContext
from trendalgo.device.crash_capture.pending_crash import clear_pending_crash, read_pending_crash
from trendalgo.device.feedback import copy as C
from trendalgo.device.feedback.preview import can_submit_feedback, feedback_preview_text
from trendalgo.device.github_feedback.issue_form_url import (
    build_issue_form_url,
    is_placeholder_repo,
)
from trendalgo.device.github_feedback.release_repo import load_release_repo
from trendalgo.device.privacy_report.fingerprint import fingerprint_crash
from trendalgo.device.privacy_report.sanitize import sanitize_report_text

FeedbackKind = Literal["bug", "feature"]


class FeedbackDialog(QDialog):
    def __init__(
        self,
        ctx: DeviceContext,
        kind: FeedbackKind,
        *,
        release_repo: str = "",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._kind = kind
        self._release_repo = release_repo.strip() or load_release_repo()
        pending = read_pending_crash(ctx.root)
        self._stack = pending.stack if pending else ""
        self.setWindowTitle(C.BUG_TITLE if kind == "bug" else C.FEATURE_TITLE)
        self.setObjectName("feedbackDialog")
        self.setAccessibleName(self.windowTitle())
        hint = QLabel(C.CLIPBOARD_HINT)
        hint.setWordWrap(True)
        self._description = QPlainTextEdit()
        self._description.setPlaceholderText(C.DESCRIPTION)
        self._description.setAccessibleName(C.DESCRIPTION)
        self._description.setMinimumHeight(100)
        if description.strip():
            self._description.setPlainText(sanitize_report_text(description))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setAccessibleName(C.PREVIEW)
        self._preview.setMinimumHeight(160)
        self._status = QLabel()
        self._status.setObjectName("hint")
        self._status.setWordWrap(True)
        buttons = QDialogButtonBox()
        self._copy = buttons.addButton(C.COPY, QDialogButtonBox.ButtonRole.ActionRole)
        self._open = buttons.addButton(C.OPEN_GITHUB, QDialogButtonBox.ButtonRole.ActionRole)
        self._discard = buttons.addButton(C.DISCARD, QDialogButtonBox.ButtonRole.RejectRole)
        self._copy.clicked.connect(self._on_copy)
        self._open.clicked.connect(self._on_open)
        self._discard.clicked.connect(self.reject)
        self._description.textChanged.connect(self._refresh)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self._description)
        layout.addWidget(QLabel(C.PREVIEW))
        layout.addWidget(self._preview)
        layout.addWidget(self._status)
        layout.addWidget(buttons)
        self._refresh()

    def _markdown(self) -> str:
        stack = self._stack or None
        return feedback_preview_text(
            kind=self._kind,
            description=self._description.toPlainText(),
            stack=stack,
            fingerprint=fingerprint_crash(stack) if stack else None,
            app_version=__version__,
            os_family=platform.system() or None,
        )

    def _refresh(self) -> None:
        self._preview.setPlainText(self._markdown())
        can = can_submit_feedback(self._description.toPlainText(), self._stack or None)
        if is_placeholder_repo(self._release_repo):
            self._open.setEnabled(False)
            self._status.setText(C.NO_REPO)
        elif not can:
            self._open.setEnabled(False)
            self._status.setText(C.NEED_TEXT)
        else:
            self._open.setEnabled(True)
            self._status.setText("")

    def _on_copy(self) -> None:
        clip = QGuiApplication.clipboard()
        if clip is None:
            self._status.setText(C.COPY_FAILED)
            return
        clip.setText(self._markdown())
        self._status.setText(C.COPIED)

    def _on_open(self) -> None:
        md = self._markdown()
        desc = sanitize_report_text(self._description.toPlainText())
        if self._kind == "bug":
            template = "bug_report.yml"
            fields = {"description": desc, "reproduction": md, "title": "[bug]: "}
        else:
            template = "product_idea.yml"
            fields = {"problem": desc, "solution": md, "title": "[feat]: "}
        built = build_issue_form_url(self._release_repo, template, fields)
        url = str(built.get("url") or "")
        if not url.startswith("https://"):
            return
        clip_md = built.get("clipboard_markdown")
        if built.get("body_too_large") and isinstance(clip_md, str):
            clip = QGuiApplication.clipboard()
            if clip is not None:
                clip.setText(clip_md)
        webbrowser.open(url, new=2)

    def reject(self) -> None:
        clip = QGuiApplication.clipboard()
        if clip is not None:
            clip.setText("")
        clear_pending_crash(self._ctx.root)
        super().reject()


def open_feedback(
    ctx: DeviceContext,
    kind: FeedbackKind,
    *,
    parent: QWidget | None = None,
    release_repo: str = "",
    description: str = "",
) -> None:
    FeedbackDialog(
        ctx,
        kind,
        release_repo=release_repo,
        description=description,
        parent=parent,
    ).exec()
