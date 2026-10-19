"""Secret Sauce product names (TA coincidence vs Lab deep mine)."""

from __future__ import annotations

SAUCE_TA = "Secret Sauce TA"
SAUCE_LAB = "Secret Sauce Lab"
# Legacy single name — treat as Lab for clicks / tint.
SAUCE_LEGACY = "Secret Sauce"
SAUCE_ALL = frozenset({SAUCE_TA, SAUCE_LAB, SAUCE_LEGACY})


def is_sauce(name: object) -> bool:
    return str(name or "").strip() in SAUCE_ALL


def is_sauce_lab(name: object) -> bool:
    text = str(name or "").strip()
    return text in {SAUCE_LAB, SAUCE_LEGACY}


def is_sauce_ta(name: object) -> bool:
    return str(name or "").strip() == SAUCE_TA
