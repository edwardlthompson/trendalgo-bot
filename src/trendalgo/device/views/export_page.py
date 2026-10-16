"""Export hub: journal CSV, plan JSON, and latest scan JSON into a chosen folder."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.export_model import (
    default_export_dir,
    write_journal_csv,
    write_plan_json,
    write_scan_json,
)
from trendalgo.device.views.widgets import (
    clear_problem,
    field,
    page_header,
    problem_label,
    show_problem,
)


class ExportPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._dest = default_export_dir(ctx.root)
        self._folder = QLabel()
        self._folder.setObjectName("hint")
        self._folder.setWordWrap(True)
        self._status = QLabel()
        self._status.setObjectName("hint")
        self._problem = problem_label()
        self._choose = QPushButton(S.EXPORT_CHOOSE_FOLDER)
        self._choose.clicked.connect(lambda _checked=False: self._pick_folder())
        self._journal = QPushButton(S.EXPORT_JOURNAL)
        self._journal.clicked.connect(lambda _checked=False: self._export_journal())
        self._plan = QPushButton(S.EXPORT_PLAN)
        self._plan.clicked.connect(lambda _checked=False: self._export_plan())
        self._scan = QPushButton(S.EXPORT_SCAN)
        self._scan.clicked.connect(lambda _checked=False: self._export_scan())
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.EXPORT_TITLE, S.EXPORT_SUBTITLE))
        layout.addWidget(self._problem)
        layout.addWidget(field(S.EXPORT_FOLDER_FIELD, self._folder, S.EXPORT_FOLDER_HELP))
        layout.addWidget(self._choose, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._journal, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._plan, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._scan, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)
        layout.addStretch(1)
        self._refresh_folder_label()

    def _pick_folder(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, S.EXPORT_CHOOSE_FOLDER, str(self._dest))
        if chosen:
            self._dest = Path(chosen)
            clear_problem(self._problem)
            self._refresh_folder_label()

    def _refresh_folder_label(self) -> None:
        self._folder.setText(S.EXPORT_FOLDER_LABEL.format(path=self._dest))

    def _export_journal(self) -> None:
        self._run_export(
            lambda: write_journal_csv(self._dest, self._ctx.databases["journal"]),
            missing=S.EXPORT_NO_JOURNAL,
        )

    def _export_plan(self) -> None:
        self._run_export(
            lambda: write_plan_json(self._dest, self._ctx.plan_path),
            missing=S.EXPORT_NO_PLAN,
        )

    def _export_scan(self) -> None:
        self._run_export(
            lambda: write_scan_json(self._dest, self._ctx.databases["scanner"]),
            missing=S.EXPORT_NO_SCAN,
        )

    def _run_export(self, action: Callable[[], Path], *, missing: str) -> None:
        clear_problem(self._problem)
        self._status.clear()
        try:
            path = action()
        except FileNotFoundError:
            show_problem(self._problem, missing)
            return
        except OSError as exc:
            show_problem(self._problem, str(exc))
            return
        self._status.setText(S.EXPORT_DONE.format(name=path.name, path=path))
