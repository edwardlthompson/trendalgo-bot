"""About: version row, Check for updates, Changelog link."""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo import __version__
from trendalgo.device import strings as S
from trendalgo.device.about.github_release import changelog_url, release_page_url
from trendalgo.device.about.run_updates import check_for_update
from trendalgo.device.context import DeviceContext
from trendalgo.device.github_feedback.release_repo import load_release_repo
from trendalgo.device.views.launch_prompt_dialog import offer_launch_prompt
from trendalgo.device.views.widgets import mark_primary


class AboutUpdatesSection(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        version = QLabel(S.ABOUT_VERSION.format(version=__version__))
        version.setObjectName("aboutVersion")
        self._check = mark_primary(QPushButton(S.ABOUT_CHECK_UPDATES))
        self._check.setMinimumHeight(44)
        self._check.setAccessibleName(S.ABOUT_CHECK_UPDATES)
        self._check.clicked.connect(lambda _c=False: self._run_check())
        self._changelog = QPushButton(S.ABOUT_CHANGELOG)
        self._changelog.setMinimumHeight(44)
        self._changelog.setAccessibleName(S.ABOUT_CHANGELOG)
        self._changelog.clicked.connect(lambda _c=False: self._open_changelog())
        self._status = QLabel()
        self._status.setObjectName("hint")
        self._status.setWordWrap(True)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(version, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._check)
        row.addWidget(self._changelog)
        row.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addLayout(row)
        layout.addWidget(self._status)

    def _run_check(self) -> None:
        self._check.setEnabled(False)
        self._status.setText(S.ABOUT_UPDATE_CHECKING)
        try:
            result = check_for_update(
                self._ctx.root,
                current_version=__version__,
                interval="launch",
                force=True,
            )
        except Exception:  # noqa: BLE001 — keep About alive on unexpected errors
            self._status.setText(S.ABOUT_UPDATE_ERROR)
            self._check.setEnabled(True)
            return
        self._check.setEnabled(True)
        if result.status == "error":
            self._status.setText(S.ABOUT_UPDATE_ERROR)
            return
        if result.status == "current" or result.prompt is None:
            self._status.setText(S.ABOUT_UPDATE_CURRENT)
            return
        if result.status == "donate":
            offer_launch_prompt(
                self._ctx, result.prompt, current_version=__version__, parent=self.window()
            )
            self._status.clear()
            return
        self._status.setText(S.ABOUT_UPDATE_AVAILABLE.format(version=result.prompt.version))
        offer_launch_prompt(
            self._ctx, result.prompt, current_version=__version__, parent=self.window()
        )

    def _open_changelog(self) -> None:
        repo = load_release_repo()
        url = changelog_url(repo) if repo else ""
        if not url:
            url = release_page_url(repo) if repo else ""
        if not url:
            self._status.setText(S.ABOUT_UPDATE_ERROR)
            return
        webbrowser.open(url, new=2)
