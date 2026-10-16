"""Compute which nav items fit in the tab bar vs overflow into More."""

from __future__ import annotations

from dataclasses import dataclass

from trendalgo.device import strings as S

# Primary workflow: Portfolio → Alerts → Scanner → Backtest → Bots
PORTFOLIO, ALERTS, SCANNER, BACKTESTS, STATUS = range(5)
GLOSSARY, EXPORT, BILLING, SETTINGS, DEBUG = range(5, 10)
# Legacy aliases: Plan/Research/AI removed from chrome; Plan redirects to Bots.
PLAN = STATUS
RESEARCH = EXPORT
AI = BILLING
PRIMARY_COUNT = 5
PRIMARY_GLYPHS = ("portfolio", "alerts", "scanner", "backtest", "bot")
MORE_ITEMS: tuple[tuple[int, str, str], ...] = (
    (GLOSSARY, S.NAV_GLOSSARY, "glossary"),
    (EXPORT, S.NAV_EXPORT, "export"),
    (BILLING, S.NAV_BILLING, "billing"),
    (SETTINGS, S.NAV_SETTINGS, "settings"),
    (DEBUG, S.NAV_DEBUG, "debug"),
)


@dataclass(frozen=True)
class NavItem:
    index: int
    label: str
    glyph: str


NAV_CATALOG: tuple[NavItem, ...] = (
    NavItem(PORTFOLIO, S.NAV_PORTFOLIO, "portfolio"),
    NavItem(ALERTS, S.NAV_ALERTS, "alerts"),
    NavItem(SCANNER, S.NAV_SCANNER, "scanner"),
    NavItem(BACKTESTS, S.NAV_BACKTESTS, "backtest"),
    NavItem(STATUS, S.NAV_STATUS, "bot"),
    NavItem(GLOSSARY, S.NAV_GLOSSARY, "glossary"),
    NavItem(EXPORT, S.NAV_EXPORT, "export"),
    NavItem(BILLING, S.NAV_BILLING, "billing"),
    NavItem(SETTINGS, S.NAV_SETTINGS, "settings"),
    NavItem(DEBUG, S.NAV_DEBUG, "debug"),
)

NAV_BY_GLYPH: dict[str, int] = {item.glyph: item.index for item in NAV_CATALOG}
NAV_GLYPH_BY_INDEX: dict[int, str] = {item.index: item.glyph for item in NAV_CATALOG}

# Pre-Alerts top-level layout (9 tabs). Migrate saved int indices once.
LEGACY_INT_TO_GLYPH: dict[int, str] = {
    0: "portfolio",
    1: "scanner",
    2: "backtest",
    3: "bot",
    4: "glossary",
    5: "export",
    6: "billing",
    7: "settings",
    8: "debug",
}


def pack_nav(
    items: tuple[NavItem, ...],
    *,
    available_width: int,
    tab_widths: list[int],
    more_width: int,
) -> tuple[list[NavItem], list[NavItem]]:
    """Split items into visible tabs and More overflow.

    Reserves space for More only when at least one item would overflow.
    """
    if not items:
        return [], []
    widths = list(tab_widths)
    while len(widths) < len(items):
        widths.append(80)
    used = 0
    for i, _item in enumerate(items):
        w = max(1, widths[i])
        if used + w > available_width:
            break
        used += w
    else:
        return list(items), []

    budget = max(0, available_width - max(1, more_width))
    visible: list[NavItem] = []
    used = 0
    for i, item in enumerate(items):
        w = max(1, widths[i])
        if used + w > budget:
            return visible, list(items[i:])
        visible.append(item)
        used += w
    return visible, []
