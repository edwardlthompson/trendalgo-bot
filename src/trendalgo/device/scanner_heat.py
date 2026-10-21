"""Relative green→yellow→red rank colors for Opportunity scanner numeric cells."""

from __future__ import annotations

from collections.abc import Sequence

from trendalgo.device import design_tokens as T

# Columns where algebraically higher = better (less risk).
INVERT_KEYS = frozenset({"hv7", "mdd"})

# Heat column key → table column index (Watch|Logo|Name layout).
HEAT_COL_KEYS: dict[int, str] = {
    3: "g7pct",
    5: "g30pct",
    7: "btbest",
    8: "btvbh",
    9: "uniformity",
    10: "health",
    11: "hv7",
    12: "mdd",
    13: "volaccel",
    15: "vol24h",
}

# RGB stops (no raw hex literals — device UI token rule).
_RED = (220, 38, 38)
_YELLOW = (234, 179, 8)
_GREEN = (22, 163, 74)


def fg_for_bg(hex_bg: str) -> str:
    """Near-black or white text for contrast on a filled cell background."""
    if _luminance(hex_bg) > 0.45:
        return T.LIGHT["onBackground"]
    return T.LIGHT["onPrimary"]


def rank_hex_colors(
    values: Sequence[float | None],
    *,
    invert: bool = False,
) -> list[str | None]:
    """Map values to green→yellow→red by unique value (ties share a color). Best=green."""
    ranked = [(i, v) for i, v in enumerate(values) if v is not None and v == v]
    out: list[str | None] = [None] * len(values)
    if not ranked:
        return out
    # Bucket by rounded key so 100.0 and 100.0001 match; identicals share one color.
    buckets: dict[float, list[int]] = {}
    for index, value in ranked:
        key = round(float(value), 8)
        buckets.setdefault(key, []).append(index)
    unique = sorted(buckets.keys(), reverse=not invert)
    if len(unique) == 1:
        color = _lerp_ryg(1.0)  # solid best (green)
        for index in buckets[unique[0]]:
            out[index] = color
        return out
    last = len(unique) - 1
    for place, key in enumerate(unique):
        t = 1.0 - (place / last)
        color = _lerp_ryg(t)
        for index in buckets[key]:
            out[index] = color
    return out


def _lerp_ryg(t: float) -> str:
    """t=0 red, t=0.5 yellow, t=1 green."""
    t = max(0.0, min(1.0, t))
    if t <= 0.5:
        return _mix(_RED, _YELLOW, t * 2.0)
    return _mix(_YELLOW, _GREEN, (t - 0.5) * 2.0)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], u: float) -> str:
    rgb = tuple(int(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return "#" + "".join(f"{channel:02X}" for channel in rgb)


def _luminance(hex_color: str) -> float:
    digits = hex_color.lstrip("#")
    if len(digits) < 6:
        return 0.0
    linear = []
    for index in (0, 2, 4):
        channel = int(digits[index : index + 2], 16) / 255
        if channel <= 0.03928:
            linear.append(channel / 12.92)
        else:
            linear.append(((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
