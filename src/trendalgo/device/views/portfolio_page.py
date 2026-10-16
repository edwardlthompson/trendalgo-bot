"""Portfolio page: CoinStats-style sub-tabs, demo Top-20, Share PNG."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_client import HostRefusedError
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.portfolio_demo import is_demo_source, seed_demo_portfolio
from trendalgo.device.portfolio_model import PortfolioOverview, equity_for_range
from trendalgo.device.portfolio_share import share_widget_png
from trendalgo.device.portfolio_sync import apply_host_portfolio
from trendalgo.device.stores import StoreReadError, read_portfolio
from trendalgo.device.views.equity_chart import EquityChart
from trendalgo.device.views.holdings_heatmap import HoldingsHeatmap
from trendalgo.device.views.portfolio_advanced_panel import PortfolioAdvancedPanel
from trendalgo.device.views.portfolio_allocation_bar import PortfolioAllocationBar
from trendalgo.device.views.portfolio_hero import PortfolioHero, money, pl_lines, signed_money
from trendalgo.device.views.portfolio_timeline import PortfolioTimeline
from trendalgo.device.views.widgets import (
    TailFill,
    clear_problem,
    fill_table,
    mark_primary,
    page_header,
    problem_label,
    read_only_table,
    show_problem,
    tint_signed,
)
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.metrics import heatmap_rows
from trendalgo.portfolio.performance import PERFORMANCE_RANGES

_DUST_USD = 1.0


class PortfolioPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._path: Path | None = ctx.portfolio_path
        self._as_of: str | None = None
        self._range = "1y"
        self._hide_dust = False
        self._overview: PortfolioOverview | None = None
        self._reload = QPushButton(S.RELOAD)
        self._reload.clicked.connect(lambda _c=False: self.reload())
        self._sync = mark_primary(QPushButton(S.PORTFOLIO_SYNC))
        self._sync.clicked.connect(lambda _c=False: self._sync_from_host())
        self._share = QPushButton(S.PORTFOLIO_SHARE)
        self._share.setToolTip(S.PORTFOLIO_SHARE_TIP)
        self._share.clicked.connect(lambda _c=False: self._share_png())
        self._export = QPushButton(S.PORTFOLIO_EXPORT_CSV)
        self._export.clicked.connect(lambda _c=False: self._export_csv())
        self._demo_btn = QPushButton(S.PORTFOLIO_LOAD_DEMO)
        self._demo_btn.setToolTip(S.PORTFOLIO_DEMO_TIP)
        self._demo_btn.clicked.connect(lambda _c=False: self._toggle_demo())
        self._demo = QLabel(S.PORTFOLIO_DEMO_BADGE)
        self._demo.setObjectName("badge")
        self._demo.hide()
        self._demo_mode = False
        self._real_path: Path | None = ctx.portfolio_path
        self._dust = QCheckBox(S.PORTFOLIO_HIDE_DUST)
        self._dust.toggled.connect(self._on_dust)
        self._range_box = QComboBox()
        self._range_box.addItems(list(PERFORMANCE_RANGES.keys()))
        self._range_box.setCurrentText(self._range)
        self._range_box.currentTextChanged.connect(self._on_range)
        self._problem = problem_label()
        self._caption = QLabel()
        self._caption.setObjectName("hint")
        self._caption.setWordWrap(True)
        self._tabs = QTabBar()
        for label in (
            S.PORTFOLIO_TAB_OVERVIEW,
            S.PORTFOLIO_TAB_HOLDINGS,
            S.PORTFOLIO_TAB_ANALYTICS,
            S.PORTFOLIO_TAB_TOOLS,
        ):
            self._tabs.addTab(label)
        self._tabs.currentChanged.connect(self._on_tab)
        self._stack = QStackedWidget()
        self._timeline = PortfolioTimeline(self._on_timeline_date)
        self._hero = PortfolioHero()
        self._chart = EquityChart()
        self._alloc = PortfolioAllocationBar()
        self._heatmap = HoldingsHeatmap()
        self._table = read_only_table(S.PORTFOLIO_HEADERS, S.PORTFOLIO_HOLDINGS)
        self._gainers = QLabel("—")
        self._gainers.setWordWrap(True)
        self._losers = QLabel("—")
        self._losers.setWordWrap(True)
        self._bench = QLabel(S.PORTFOLIO_VS_BENCHMARKS)
        self._bench.setObjectName("hint")
        self._advanced = PortfolioAdvancedPanel()
        self._stack.addWidget(self._build_overview())
        self._stack.addWidget(self._build_holdings())
        self._stack.addWidget(self._build_analytics())
        self._stack.addWidget(self._advanced)
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.PORTFOLIO_TITLE, S.PORTFOLIO_SUBTITLE))
        actions = QHBoxLayout()
        for w in (
            self._reload,
            self._sync,
            self._share,
            self._export,
            self._demo_btn,
            self._demo,
        ):
            actions.addWidget(w)
        actions.addWidget(self._dust)
        actions.addWidget(QLabel(S.PORTFOLIO_RANGE))
        actions.addWidget(self._range_box)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addWidget(self._problem)
        layout.addWidget(self._caption)
        layout.addWidget(self._tabs)
        layout.addWidget(self._stack, 1)
        self._fill = TailFill(layout, self._stack)
        self.reload()

    def _build_overview(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._timeline)
        lay.addWidget(self._hero)
        lay.addWidget(self._chart, 1)
        lay.addWidget(self._alloc)
        return page

    def _build_holdings(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._heatmap)
        lay.addWidget(self._table, 1)
        return page

    def _build_analytics(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(S.PORTFOLIO_GAINERS))
        lay.addWidget(self._gainers)
        lay.addWidget(QLabel(S.PORTFOLIO_LOSERS))
        lay.addWidget(self._losers)
        lay.addWidget(self._bench)
        lay.addStretch(1)
        return page

    def _on_tab(self, index: int) -> None:
        self._stack.setCurrentIndex(max(0, index))

    def _on_dust(self, checked: bool) -> None:
        self._hide_dust = checked
        if self._overview is not None:
            self._fill_holdings(self._overview)

    def _on_range(self, key: str) -> None:
        self._range = key or "1y"
        if self._overview is not None:
            self._apply_chart(self._overview)

    def _share_png(self) -> None:
        tab = self._tabs.tabText(self._tabs.currentIndex()) or "overview"
        try:
            out = share_widget_png(self._stack.currentWidget() or self, self._ctx.root, tab=tab)
        except OSError as exc:
            show_problem(self._problem, str(exc))
            return
        clear_problem(self._problem)
        self._caption.setText(S.PORTFOLIO_SHARE_DONE.format(name=out.name, path=out))

    def _toggle_demo(self) -> None:
        if self._demo_mode:
            self._demo_mode = False
            self._path = self._real_path
            self._demo_btn.setText(S.PORTFOLIO_LOAD_DEMO)
            self.reload()
            return
        demo_path = self._ctx.root / "portfolio-demo.db"
        seed_demo_portfolio(demo_path)
        if self._path is not None and self._path.resolve() != demo_path.resolve():
            self._real_path = self._path
        elif self._ctx.portfolio_path is not None:
            self._real_path = self._ctx.portfolio_path
        self._demo_mode = True
        self._path = demo_path
        self._demo_btn.setText(S.PORTFOLIO_EXIT_DEMO)
        self._as_of = None
        self.reload()

    def _sync_from_host(self) -> None:
        client = try_open_host_client(self._ctx.settings_path)
        if client is None:
            show_problem(self._problem, S.PORTFOLIO_SYNC_NO_HOST)
            return
        try:
            response = client.get_portfolio()
        except HostRefusedError as exc:
            show_problem(self._problem, exc.problem.message)
            return
        if response.status == 0:
            show_problem(self._problem, S.PORTFOLIO_SYNC_UNREACHABLE)
            return
        if not response.ok:
            show_problem(self._problem, S.PORTFOLIO_SYNC_REFUSED)
            return
        data = response.data or {}
        if not data.get("snapshot"):
            show_problem(self._problem, S.PORTFOLIO_SYNC_EMPTY)
            return
        dest = self._real_path or self._ctx.portfolio_path or (self._ctx.root / "portfolio.db")
        if apply_host_portfolio(Path(dest), data):
            self._demo_mode = False
            self._real_path = Path(dest)
            self._path = Path(dest)
            self._demo_btn.setText(S.PORTFOLIO_LOAD_DEMO)
            clear_problem(self._problem)
            self._caption.setText(S.PORTFOLIO_SYNC_APPLIED)
            self.reload()
            return
        show_problem(self._problem, S.PORTFOLIO_SYNC_EMPTY)

    def _export_csv(self) -> None:
        path = self._path
        if path is None or not path.is_file():
            show_problem(self._problem, S.PORTFOLIO_EMPTY_BODY)
            return
        try:
            store = PortfolioStore(path, create=False)
            accounts = store.list_accounts()
            if not accounts:
                show_problem(self._problem, S.PORTFOLIO_EMPTY_BODY)
                return
            csv_text = store.export_holdings_csv(int(accounts[0]["id"]))
            out = self._ctx.root / "exports" / "portfolio-holdings.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(csv_text, encoding="utf-8")
            clear_problem(self._problem)
            self._caption.setText(S.EXPORT_DONE.format(name=out.name, path=out))
        except Exception as exc:
            show_problem(self._problem, str(exc))

    def reload(self) -> None:
        path: Path
        if self._demo_mode:
            path = self._path if self._path is not None else (self._ctx.root / "portfolio-demo.db")
            if not path.is_file():
                seed_demo_portfolio(path)
        else:
            candidate = self._path or self._ctx.portfolio_path
            if candidate is None or not candidate.is_file():
                # No real portfolio yet — auto-seed demo so the page is not blank.
                path = self._ctx.root / "portfolio-demo.db"
                seed_demo_portfolio(path)
                self._demo_mode = True
                self._demo_btn.setText(S.PORTFOLIO_EXIT_DEMO)
                self._path = path
            else:
                path = candidate
        try:
            overview = read_portfolio(path, as_of_date=self._as_of)
        except StoreReadError as exc:
            show_problem(self._problem, str(exc))
            return
        clear_problem(self._problem)
        if overview is None and self._demo_mode:
            seed_demo_portfolio(path)
            overview = read_portfolio(path, as_of_date=self._as_of)
        if overview is None:
            show_problem(self._problem, S.PORTFOLIO_EMPTY_BODY)
            return
        self._path = path
        self._apply_overview(overview)

    def _on_timeline_date(self, day: str) -> None:
        self._as_of = day
        self.reload()

    def _apply_overview(self, overview: PortfolioOverview) -> None:
        self._overview = overview
        demo = self._demo_mode or is_demo_source(overview.source)
        self._demo.setVisible(demo)
        self._demo_btn.setText(S.PORTFOLIO_EXIT_DEMO if demo else S.PORTFOLIO_LOAD_DEMO)
        if demo:
            self._demo_mode = True
        dates = list(overview.snapshot_dates)
        if len(dates) >= 2 and self._as_of is None:
            self._as_of = dates[0]
        self._timeline.set_dates(dates, selected=self._as_of)
        if demo:
            self._caption.setText(S.PORTFOLIO_DEMO_CAPTION)
        else:
            self._caption.setText(
                f"{S.PORTFOLIO_CAPTION} {S.PORTFOLIO_AS_OF.format(when=overview.captured_at)}"
            )
        self._hero.set_overview(overview)
        self._apply_chart(overview)
        self._alloc.set_allocation(list(overview.allocation))
        self._heatmap.set_rows(heatmap_rows(overview.holdings))
        self._fill_holdings(overview)
        ranked = sorted(
            overview.holdings,
            key=lambda h: float(h.get("unrealized_pnl_usd") or 0),
            reverse=True,
        )
        self._gainers.setText(pl_lines(ranked[:3]) or "—")
        losers = list(reversed(ranked[-3:])) if ranked else []
        self._losers.setText(pl_lines(losers) or "—")
        self._advanced.set_overview(overview)
        self._fill.update(True)

    def _apply_chart(self, overview: PortfolioOverview) -> None:
        equity = list(overview.equity)
        try:
            ranged = equity_for_range(overview.path, self._range)
            if len(ranged) >= 2:
                equity = ranged
        except Exception:
            pass
        self._chart.set_curves(
            equity,
            top10=list(overview.compare_top10),
            buy_hold=list(overview.compare_buy_hold),
        )

    def _fill_holdings(self, overview: PortfolioOverview) -> None:
        rows = list(overview.holdings)
        if self._hide_dust:
            rows = [h for h in rows if float(h.get("value_usd") or 0) >= _DUST_USD]
        rows.sort(key=lambda h: float(h.get("value_usd") or 0), reverse=True)
        fill_table(
            self._table,
            [
                (
                    str(h.get("asset", "")),
                    f"{float(h.get('allocation_pct') or 0) * 100:.1f}%",
                    money(h.get("quantity")),
                    money(h.get("price_usd")),
                    money(h.get("value_usd")),
                    money(h.get("cost_basis_usd")),
                    signed_money(h.get("unrealized_pnl_usd")),
                    str(h.get("tag") or "—"),
                )
                for h in rows
            ],
        )
        for index, holding in enumerate(rows):
            item = self._table.item(index, 6)
            if item is not None:
                try:
                    tint_signed(item, float(holding.get("unrealized_pnl_usd", 0)))
                except (TypeError, ValueError):
                    pass
