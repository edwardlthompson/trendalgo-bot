"""Assets holdings table with CoinStats-style columns."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.portfolio_hero import money, signed_money
from trendalgo.device.views.widgets import read_only_table

# Column index → sort key
_COL_SORT = ("name", "amount", "change_24h", "price", "total", "avg_buy", "profit")
_DUST = 1.0


class AssetsModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._sort = "total"
        self._asc = False
        self._hide_dust = False
        self._rows: list[dict] = []
        title = QLabel("Assets")
        title.setObjectName("dashModuleTitle")
        self._dust = QCheckBox(S.PORTFOLIO_HIDE_DUST)
        self._dust.toggled.connect(self._on_dust)
        self._table = read_only_table(S.PORTFOLIO_HEADERS_RICH, S.PORTFOLIO_HOLDINGS)
        self._table.setObjectName("dashAssetsTable")
        self._table.setWordWrap(True)
        self._table.verticalHeader().setDefaultSectionSize(48)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header = self._table.horizontalHeader()
        for col in range(7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        header.setMinimumSectionSize(72)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.addWidget(title, 1)
        top.addWidget(self._dust)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addLayout(top)
        layout.addWidget(self._table, 1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        self._rows = list(overview.holdings) if overview else []
        self._render()

    def _on_header(self, index: int) -> None:
        if index < 0 or index >= len(_COL_SORT):
            return
        key = _COL_SORT[index]
        if key == self._sort:
            self._asc = not self._asc
        else:
            self._sort = key
            self._asc = key == "name"
        self._render()

    def _on_dust(self, checked: bool) -> None:
        self._hide_dust = checked
        self._render()

    def _render(self) -> None:
        rows = self._rows
        if self._hide_dust:
            rows = [r for r in rows if float(r.get("value_usd") or 0) >= _DUST]
        enriched = [_enrich(r, self._sort) for r in rows]
        enriched.sort(key=lambda r: r["_key"], reverse=not self._asc)
        colors = colors_for(active_mode())
        up = QColor(colors["gainUp"])
        down = QColor(colors["gainDown"])
        sort_col = _COL_SORT.index(self._sort) if self._sort in _COL_SORT else 4
        self._table.horizontalHeader().setSortIndicator(
            sort_col,
            Qt.SortOrder.AscendingOrder if self._asc else Qt.SortOrder.DescendingOrder,
        )
        self._table.setRowCount(len(enriched))
        for row_index, e in enumerate(enriched):
            cells = [
                e["name"],
                e["amount"],
                e["change_24h"],
                e["price"],
                e["total"],
                e["avg_buy"],
                e["profit"],
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                    if column == 0
                    else Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                if column in (2, 6) and isinstance(e.get("_signed"), float):
                    signed = float(e["_signed"] if column == 6 else e.get("_chg", 0.0))
                    if signed > 0:
                        item.setForeground(up)
                    elif signed < 0:
                        item.setForeground(down)
                self._table.setItem(row_index, column, item)


def _enrich(row: dict, sort_key: str) -> dict:
    qty = float(row.get("quantity") or 0.0)
    value = float(row.get("value_usd") or 0.0)
    cost = float(row.get("cost_basis_usd") or 0.0)
    price = float(row.get("price_usd") or 0.0)
    avg = (cost / qty) if qty > 0 else None
    pnl = float(row.get("unrealized_pnl_usd") or (value - cost))
    pnl_pct = (pnl / cost) if cost > 0 else 0.0
    change = row.get("change_24h_pct")
    chg = float(change) if isinstance(change, (int, float)) else 0.0
    if isinstance(change, (int, float)):
        arrow = "▲" if chg >= 0 else "▼"
        change_s = f"{arrow} {chg:+.2f}%"
    else:
        change_s = "—"
    avg_s = money(avg) if avg is not None else "—"
    if avg is not None and cost > 0:
        avg_s = f"{money(avg)}\n{pnl_pct:+.2%}"
    profit_s = f"{signed_money(pnl)}\n{pnl_pct:+.2%}"
    asset = str(row.get("asset") or "")
    name = str(row.get("name") or asset)
    display = f"{name}  ·  {asset}" if name and name != asset else asset
    sort_map: dict[str, object] = {
        "name": asset.lower(),
        "amount": qty,
        "change_24h": chg if isinstance(change, (int, float)) else float("-inf"),
        "price": price,
        "total": value,
        "avg_buy": avg if avg is not None else float("-inf"),
        "profit": pnl,
        "allocation": float(row.get("allocation_pct") or 0.0),
        "holdings": value,
    }
    return {
        "name": display,
        "amount": _qty(qty),
        "change_24h": change_s,
        "price": money(price),
        "total": money(value),
        "avg_buy": avg_s,
        "profit": profit_s,
        "_key": sort_map.get(sort_key, value),
        "_signed": pnl,
        "_chg": chg,
    }


def _qty(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 1:
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{value:.6f}".rstrip("0").rstrip(".")
