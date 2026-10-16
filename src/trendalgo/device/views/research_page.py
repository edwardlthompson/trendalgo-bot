"""Research panel: walk-forward / Monte Carlo honesty; local correlation note export."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.export_model import default_export_dir
from trendalgo.device.research_model import (
    correlation_note_payload,
    load_portfolio_overview,
    write_correlation_note,
)
from trendalgo.device.views.widgets import (
    EmptyState,
    clear_problem,
    page_header,
    problem_label,
    section_title,
    show_problem,
)


class ResearchPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._problem = problem_label()
        self._status = QLabel()
        self._status.setObjectName("hint")
        self._corr_empty = EmptyState(
            S.RESEARCH_CORRELATION_EMPTY_TITLE, S.RESEARCH_CORRELATION_EMPTY_BODY
        )
        self._export_corr = QPushButton(S.RESEARCH_CORRELATION_EXPORT)
        self._export_corr.clicked.connect(lambda _checked=False: self._export_correlation())
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.RESEARCH_TITLE, S.RESEARCH_SUBTITLE))
        layout.addWidget(section_title(S.RESEARCH_WALK_FORWARD_TITLE))
        layout.addWidget(_hint(S.RESEARCH_WALK_FORWARD_BODY))
        layout.addWidget(section_title(S.RESEARCH_MONTE_CARLO_TITLE))
        layout.addWidget(_hint(S.RESEARCH_MONTE_CARLO_BODY))
        layout.addWidget(section_title(S.RESEARCH_CORRELATION_TITLE))
        layout.addWidget(_hint(S.RESEARCH_CORRELATION_BODY))
        layout.addWidget(self._problem)
        layout.addWidget(self._corr_empty)
        layout.addWidget(self._export_corr, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)
        layout.addStretch(1)
        self._refresh_correlation_state()

    def _refresh_correlation_state(self) -> None:
        payload = correlation_note_payload(load_portfolio_overview(self._ctx.portfolio_path))
        ready = payload is not None
        self._export_corr.setVisible(ready)
        self._corr_empty.setVisible(not ready)

    def _export_correlation(self) -> None:
        clear_problem(self._problem)
        self._status.clear()
        payload = correlation_note_payload(load_portfolio_overview(self._ctx.portfolio_path))
        if payload is None:
            show_problem(self._problem, S.RESEARCH_CORRELATION_EMPTY_BODY)
            return
        dest = default_export_dir(self._ctx.root)
        path = write_correlation_note(dest, payload)
        self._status.setText(S.EXPORT_DONE.format(name=path.name, path=path))


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("hint")
    return label
