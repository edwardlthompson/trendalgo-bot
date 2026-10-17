"""Events Calendar module with filter chips."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.calendar import cache, vault
from trendalgo.device.calendar.model import CalendarFilters, apply_filters
from trendalgo.device.calendar.refresh import refresh_cache
from trendalgo.device.context import DeviceContext
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.views.chip_bar import ChipBar
from trendalgo.device.views.widgets import mark_primary
from trendalgo.device.wizard.credentials import MemoryCredentialStore


class EventsCalendarModule(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        *,
        on_setup: Callable[[], None] | None = None,
        store: MemoryCredentialStore | None = None,
    ) -> None:
        super().__init__()
        self._ctx = ctx
        self._store = store
        self._on_setup = on_setup
        self._filters = CalendarFilters()
        self._holdings: set[str] = set()
        self._setup = mark_primary(QPushButton(S.PORTFOLIO_CALENDAR_SETUP))
        self._setup.clicked.connect(lambda _c=False: self._open_setup())
        self._refresh = QPushButton(S.CAL_EVENTS_REFRESH)
        self._refresh.clicked.connect(lambda _c=False: self._do_refresh())
        self._chips = ChipBar(
            (
                ("holdings", S.CAL_FILTER_HOLDINGS),
                ("30d", S.CAL_FILTER_30D),
                ("impact", S.CAL_FILTER_IMPACT),
                ("date", S.CAL_SORT_DATE),
                ("impact_sort", S.CAL_SORT_IMPACT),
                ("pop", S.CAL_SORT_POP),
            ),
            exclusive=False,
            on_change=self._chip,
        )
        self._list = QLabel(S.CAL_EVENTS_NO_KEYS)
        self._list.setWordWrap(True)
        self._list.setObjectName("hint")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._setup)
        lay.addWidget(self._refresh)
        lay.addWidget(self._chips)
        lay.addWidget(self._list, 1)
        self._render()

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        self._holdings = {
            str(h.get("asset") or "").upper().split("/")[0]
            for h in (overview.holdings if overview else [])
            if h.get("asset")
        }
        self._render()

    def _open_setup(self) -> None:
        if self._on_setup is not None:
            self._on_setup()
        self._render()

    def _do_refresh(self) -> None:
        try:
            refresh_cache(self._ctx.root, self._store)
        except Exception:
            pass
        self._render()

    def _chip(self, key: str) -> None:
        if key == "holdings":
            self._filters.holdings_only = not self._filters.holdings_only
        elif key == "30d":
            self._filters.horizon_days = 30
        elif key == "impact":
            self._filters.impact_min = 5.0 if self._filters.impact_min is None else None
        elif key == "date":
            self._filters.sort = "date"
        elif key == "impact_sort":
            self._filters.sort = "impact"
        elif key == "pop":
            self._filters.sort = "popularity"
        self._render()

    def _render(self) -> None:
        connected = vault.any_key_present(self._store)
        self._setup.setVisible(not connected)
        events = cache.load_events(self._ctx.root)
        if not connected and not events:
            self._list.setText(S.CAL_EVENTS_NO_KEYS)
            return
        filtered = apply_filters(events, self._filters, holding_symbols=self._holdings)
        if not filtered:
            self._list.setText(S.CAL_EVENTS_EMPTY)
            return
        lines = []
        for event in filtered[:40]:
            impact = f" · impact {event.impact:.1f}" if event.impact is not None else ""
            coins = ",".join(event.coins[:3])
            lines.append(
                f"{event.displayed_date}  {event.title}  [{coins}]{impact}  ({event.source})"
            )
        self._list.setText("\n".join(lines))
