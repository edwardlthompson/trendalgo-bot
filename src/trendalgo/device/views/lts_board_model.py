"""Lean LTS board model: sort/filter index over coin dicts (SQLite/JSON projection)."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from trendalgo.device import strings as S
from trendalgo.device.lts_scan_model import cell_gain, dash
from trendalgo.device.scanner_sort import COL_SORT_KEYS, field_value, sort_coins
from trendalgo.device.views.scanner_table import COLUMNS
from trendalgo.scanner.backtest_edge import bot_vs_bh_cell_tip

__all__ = ["LtsBoardModel", "cap_board_rows"]


def cap_board_rows(
    coins: list[dict[str, Any]],
    *,
    max_symbols: int | None,
) -> list[dict[str, Any]]:
    """Enforce max_symbols so stale oversized LTS boards never hydrate the UI."""
    if max_symbols is None or max_symbols <= 0:
        return list(coins)
    return list(coins[: int(max_symbols)])


class LtsBoardModel(QAbstractTableModel):
    """Read-only table model — delegates paint logos/sparks; no per-cell QWidgets."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._coins: list[dict[str, Any]] = []
        self._sort_key = ""
        self._sort_dir = -1

    def set_coins(
        self,
        coins: list[dict[str, Any]],
        *,
        sort_key: str = "",
        sort_dir: int = -1,
    ) -> None:
        self.beginResetModel()
        self._sort_key = sort_key
        self._sort_dir = sort_dir
        self._coins = (
            sort_coins(list(coins), key=sort_key, direction=sort_dir) if sort_key else list(coins)
        )
        self.endResetModel()

    def coins(self) -> list[dict[str, Any]]:
        return list(self._coins)

    def coin_at(self, row: int) -> dict[str, Any] | None:
        if 0 <= row < len(self._coins):
            return self._coins[row]
        return None

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return len(self._coins)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        if parent is not None and parent.isValid():
            return 0
        return COLUMNS

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == int(Qt.ItemDataRole.ToolTipRole):
            tips = S.SCANNER_LTS_HEADER_TIPS
            if 0 <= section < len(tips):
                return tips[section]
            return None
        if role != int(Qt.ItemDataRole.DisplayRole):
            return None
        headers = S.SCANNER_LTS_HEADERS
        if 0 <= section < len(headers):
            return headers[section]
        return None

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        coin = self.coin_at(index.row())
        if coin is None:
            return None
        if role == int(Qt.ItemDataRole.UserRole):
            return coin
        if role == int(Qt.ItemDataRole.ToolTipRole):
            if index.column() == 8:
                return bot_vs_bh_cell_tip(coin)
            return None
        if role != int(Qt.ItemDataRole.DisplayRole):
            return None
        col = index.column()
        if col == 2:
            if str(coin.get("exchange_id") or "").strip().lower() == "forex":
                return str(coin.get("pair") or coin.get("name") or coin.get("symbol") or "")
            return str(coin.get("name") or coin.get("symbol") or "")
        if col == 3:
            return dash(cell_gain(coin, "7d"), pct=True)
        if col == 5:
            return dash(cell_gain(coin, "30d"), pct=True)
        if col == 8:
            return dash(coin.get("bot_vs_bh_pct"), pct=True, pct_digits=2)
        if col == 9:
            return dash(coin.get("health_score"))
        if col == 10:
            return dash(coin.get("hv_7d_pct"), pct=True)
        if col == 11:
            return dash(coin.get("max_drawdown_pct"), pct=True)
        if col == 12:
            return dash(coin.get("volume_acceleration_pct"), pct=True)
        if col == 14:
            from trendalgo.device.lts_scan_model import volume_display

            return volume_display(coin)
        key = COL_SORT_KEYS.get(col)
        if key:
            raw = field_value(coin, key)
            return "" if raw is None else str(raw)
        return ""
