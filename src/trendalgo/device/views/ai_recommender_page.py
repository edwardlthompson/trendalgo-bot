"""AI strategies: operator-curated presets and local rule-based recommendations."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.ai_model import curated_library, device_recommendations
from trendalgo.device.context import DeviceContext
from trendalgo.device.views.widgets import (
    EmptyState,
    fill_table,
    page_header,
    read_only_table,
    section_title,
)


class AiRecommenderPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        library = curated_library()
        presets = library.get("presets") or []
        self._curated = read_only_table(S.AI_CURATED_HEADERS, S.AI_CURATED_SECTION)
        fill_table(
            self._curated,
            [
                (
                    str(row.get("label", "")),
                    str(row.get("strategy_id", "")),
                    str(row.get("version", "")),
                )
                for row in presets
            ],
        )
        self._curated_empty = EmptyState(S.AI_CURATED_EMPTY_TITLE, S.AI_CURATED_EMPTY_BODY)
        self._curated_empty.setVisible(not presets)
        self._curated.setVisible(bool(presets))
        payload = device_recommendations(
            scanner_db=self._ctx.databases["scanner"],
            portfolio_db=self._ctx.portfolio_path,
        )
        has_scan = bool(payload.get("has_scanner_data"))
        recs = (payload.get("recommendations") or []) if has_scan else []
        self._recs = read_only_table(S.AI_RECS_HEADERS, S.AI_RECS_SECTION)
        fill_table(
            self._recs,
            [
                (
                    str(row.get("strategy_id", "")),
                    f"{row.get('score', '')}",
                    "; ".join(row.get("reasons") or []) or S.AI_RECS_NO_REASON,
                )
                for row in recs[:10]
            ],
        )
        self._recs_empty = EmptyState(S.AI_RECS_EMPTY_TITLE, S.AI_RECS_EMPTY_BODY)
        self._recs.setVisible(has_scan and bool(recs))
        self._recs_empty.setVisible(not has_scan)
        how = QLabel(S.AI_HOW_IT_WORKS)
        how.setWordWrap(True)
        how.setObjectName("hint")
        disclaimer = QLabel(str(payload.get("disclaimer", "")))
        disclaimer.setWordWrap(True)
        disclaimer.setObjectName("hint")
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.AI_TITLE, S.AI_SUBTITLE))
        layout.addWidget(how)
        layout.addWidget(section_title(S.AI_CURATED_SECTION))
        layout.addWidget(self._curated_empty)
        layout.addWidget(self._curated)
        layout.addWidget(section_title(S.AI_RECS_SECTION))
        layout.addWidget(self._recs_empty)
        layout.addWidget(self._recs)
        layout.addWidget(disclaimer)
        layout.addStretch(1)
