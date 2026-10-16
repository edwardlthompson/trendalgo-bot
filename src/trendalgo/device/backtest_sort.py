"""Sort Backtest / Results strategy rows by column key."""

from __future__ import annotations

from typing import Any

from trendalgo.device.backtest_row_filter import num_field, params_text

# Column index → sort key (Create Bot is not sortable).
COL_SORT_KEYS: dict[int, str] = {
    0: "indicator",
    1: "timeframe",
    2: "params",
    3: "net_pct",
    4: "fees_paid",
    5: "wins",
    6: "losses",
    7: "win_pct",
    8: "tsl",
    9: "tsl_hits",
    10: "tsl_hit_pct",
    11: "strength",
}

DEFAULT_SORT_KEY = "net_pct"
DEFAULT_SORT_DIR = -1  # desc
_TEXT_KEYS = frozenset({"indicator", "timeframe", "params"})


def sort_rows(
    rows: list[dict[str, Any]],
    *,
    key: str = DEFAULT_SORT_KEY,
    direction: int = DEFAULT_SORT_DIR,
) -> list[dict[str, Any]]:
    reverse = direction < 0
    if key in _TEXT_KEYS:
        return sorted(rows, key=lambda r: (_text(r, key), _net(r)), reverse=reverse)
    return sorted(
        rows,
        key=lambda r: (num_field(r, key), _net(r), str(r.get("indicator") or "").upper()),
        reverse=reverse,
    )


def _text(row: dict[str, Any], key: str) -> str:
    if key == "params":
        return params_text(row).upper()
    return str(row.get(key) or "").upper()


def _net(row: dict[str, Any]) -> float:
    return num_field(row, "net_pct")
