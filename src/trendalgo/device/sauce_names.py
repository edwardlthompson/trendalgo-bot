"""Secret Sauce product names (TA, Core Lab, helpers, Final Boss)."""

from __future__ import annotations

SAUCE_TA = "Secret Sauce TA"
SAUCE_LAB = "Secret Sauce Lab"
SAUCE_PEER = "Secret Sauce Peer"
SAUCE_ARMED = "Secret Sauce Armed"
SAUCE_EXIT = "Secret Sauce Exit"
SAUCE_FINAL = "Secret Sauce Final"
# Legacy single name — treat as Lab for clicks / tint.
SAUCE_LEGACY = "Secret Sauce"

SAUCE_HELPERS = frozenset({SAUCE_PEER, SAUCE_ARMED, SAUCE_EXIT})
SAUCE_ALL = frozenset(
    {SAUCE_TA, SAUCE_LAB, SAUCE_LEGACY, SAUCE_PEER, SAUCE_ARMED, SAUCE_EXIT, SAUCE_FINAL}
)


def is_sauce(name: object) -> bool:
    return str(name or "").strip() in SAUCE_ALL


def is_sauce_lab(name: object) -> bool:
    """Core Lab (+ legacy) — not helpers/Final."""
    text = str(name or "").strip()
    return text in {SAUCE_LAB, SAUCE_LEGACY}


def is_sauce_ta(name: object) -> bool:
    return str(name or "").strip() == SAUCE_TA


def is_sauce_final(name: object) -> bool:
    return str(name or "").strip() == SAUCE_FINAL


def is_sauce_helper(name: object) -> bool:
    return str(name or "").strip() in SAUCE_HELPERS


def create_bot_sauce_preference(rows: list[dict]) -> dict | None:
    """Prefer Final when present, else best Core Lab."""
    finals = [r for r in rows if is_sauce_final(r.get("indicator")) and not r.get("ss_lab_pending")]
    if finals:
        return max(finals, key=lambda r: float(r.get("net_pct") or float("-inf")))
    labs = [r for r in rows if is_sauce_lab(r.get("indicator")) and not r.get("ss_lab_pending")]
    if not labs:
        return None
    return max(labs, key=lambda r: float(r.get("net_pct") or float("-inf")))
