"""Sort LTS scanner coins by column key (data-model sort; rebuild the table after)."""

from __future__ import annotations

from typing import Any

from trendalgo.device.lts_scan_model import cell_gain

# Column index → sort key (Watch=0 Logo=1 Name=2 … Results=16).
COL_SORT_KEYS: dict[int, str] = {
    2: "symbol",
    3: "g7pct",
    4: "g7hi",
    5: "g30pct",
    6: "g30hi",
    7: "btbest",
    8: "btvbh",
    9: "uniformity",
    10: "health",
    11: "hv7",
    12: "mdd",
    13: "volaccel",
    14: "venue",
    15: "vol24h",
}

DEFAULT_SORT_KEY = "health"
DEFAULT_SORT_DIR = -1  # desc


def sort_coins(
    coins: list[dict[str, Any]],
    *,
    key: str = DEFAULT_SORT_KEY,
    direction: int = DEFAULT_SORT_DIR,
) -> list[dict[str, Any]]:
    reverse = direction < 0
    if key in ("symbol", "venue"):
        return sorted(coins, key=lambda c: _text(c, key), reverse=reverse)
    return sorted(
        coins,
        key=lambda c: (_num(_field(c, key)), str(c.get("symbol") or "").upper()),
        reverse=reverse,
    )


def header_label(base: str, *, active: bool, direction: int) -> str:
    """Append ▲/▼ when this column is the active sort."""
    if not active:
        return base
    return f"{base} {'▲' if direction >= 0 else '▼'}"


def _text(coin: dict[str, Any], key: str) -> str:
    if key == "venue":
        listed = coin.get("listed_on") or ["kraken"]
        return ",".join(str(x).lower() for x in listed)
    return str(coin.get("symbol") or "").upper()


def field_value(coin: dict[str, Any], key: str) -> object:
    """Numeric/text field used by sort and heatmap (same keys as COL_SORT_KEYS)."""
    return _field(coin, key)


def _field(coin: dict[str, Any], key: str) -> object:
    if key == "g7pct":
        return cell_gain(coin, "7d")
    if key == "g30pct":
        return cell_gain(coin, "30d")
    if key == "g7hi":
        return coin.get("chart_dist_7d_pct")
    if key == "g30hi":
        return coin.get("chart_dist_30d_pct")
    if key == "btbest":
        return coin.get("bot_best_net_pct")
    if key == "btvbh":
        return coin.get("bot_vs_bh_pct")
    if key == "uniformity":
        return coin.get("uniformity_score")
    if key == "health":
        return coin.get("health_score")
    if key == "hv7":
        return coin.get("hv_7d_pct")
    if key == "mdd":
        return coin.get("max_drawdown_pct")
    if key == "volaccel":
        return coin.get("volume_acceleration_pct")
    if key == "vol24h":
        return coin.get("volume_24h")
    return coin.get("health_score")


def _num(value: object) -> float:
    if value is None or isinstance(value, bool):
        return -1e18
    if isinstance(value, int | float | str):
        try:
            return float(value)
        except (TypeError, ValueError):
            return -1e18
    return -1e18
