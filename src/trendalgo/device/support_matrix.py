"""Honest venue support matrix (bundled JSON)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from trendalgo.device.bundled_data import bundled_json

Capability = Literal["yes", "no", "partial", "wallet_lp", "thin", "base_only"]
Status = Literal["supported", "partial", "coming_soon"]

_MATRIX = "support_matrix.json"
_MARK_YES = "✓"
_MARK_NO = "✗"
_MARK_PARTIAL = "partial"
_DEFAULT_ABOUT = "Research desk: Kraken today · Portfolio: 9 CEX · DEX/TradFi: coming soon."


@dataclass(frozen=True)
class VenueSupport:
    id: str
    brand: str
    lane: str
    portfolio: Capability
    public_scan: Capability
    keyed_scan: Capability
    deep_ohlcv_bt: Capability
    live_trade: Capability
    status: Status
    status_label: str
    notes: str = ""

    @property
    def public_scan_ready(self) -> bool:
        return self.public_scan == "yes"

    def badge_text(self) -> str:
        return f"{self.brand} · {self.status_label}"


def clear_support_matrix_cache() -> None:
    load_support_matrix.cache_clear()
    about_support_line.cache_clear()
    from trendalgo.device.ta_strategy_categories import clear_strategy_category_cache

    clear_strategy_category_cache()


@lru_cache(maxsize=1)
def load_support_matrix() -> tuple[VenueSupport, ...]:
    raw = bundled_json(_MATRIX)
    out: list[VenueSupport] = []
    for row in raw.get("venues") or []:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("id") or "").strip().lower()
        if not vid:
            continue
        out.append(
            VenueSupport(
                id=vid,
                brand=str(row.get("brand") or vid),
                lane=str(row.get("lane") or "cex"),
                portfolio=_cap(row.get("portfolio")),
                public_scan=_cap(row.get("public_scan")),
                keyed_scan=_cap(row.get("keyed_scan")),
                deep_ohlcv_bt=_cap(row.get("deep_ohlcv_bt")),
                live_trade=_cap(row.get("live_trade")),
                status=_status(row.get("status")),
                status_label=str(row.get("status_label") or _default_label(row.get("status"))),
                notes=str(row.get("notes") or ""),
            )
        )
    return tuple(out)


@lru_cache(maxsize=1)
def about_support_line() -> str:
    line = str(bundled_json(_MATRIX).get("about_line") or "").strip()
    return line or _DEFAULT_ABOUT


def support_footnote() -> str:
    return str(bundled_json(_MATRIX).get("footnote") or "").strip()


def venue_by_id(exchange_id: str) -> VenueSupport | None:
    eid = str(exchange_id or "").strip().lower()
    if not eid:
        return None
    for venue in load_support_matrix():
        if venue.id == eid:
            return venue
    return None


def checklist_brand(exchange_id: str, brand: str) -> str:
    """Brand label for scanner/settings when research depth is thinner than Kraken."""
    venue = venue_by_id(exchange_id)
    if venue is None:
        return brand
    if venue.public_scan_ready:
        return brand
    if venue.status == "coming_soon":
        return f"{brand} · Coming soon"
    return f"{brand} · research: Kraken-depth"


def can_keyed_chart_enrich(exchange_id: str) -> bool:
    """Keyed venues with yes/partial keyed_scan may enrich public OHLCV charts."""
    venue = venue_by_id(exchange_id)
    if venue is None:
        return False
    return venue.keyed_scan in {"yes", "partial"}


def capability_mark(value: Capability | str) -> str:
    text = str(value or "no").strip().lower()
    if text == "yes":
        return _MARK_YES
    if text == "no":
        return _MARK_NO
    if text == "partial":
        return _MARK_PARTIAL
    if text in {"wallet_lp", "thin", "base_only"}:
        return text
    return _MARK_NO


def _cap(raw: Any) -> Capability:
    text = str(raw or "no").strip().lower()
    allowed = {"yes", "no", "partial", "wallet_lp", "thin", "base_only"}
    return text if text in allowed else "no"  # type: ignore[return-value]


def _status(raw: Any) -> Status:
    text = str(raw or "coming_soon").strip().lower()
    return text if text in {"supported", "partial", "coming_soon"} else "coming_soon"  # type: ignore[return-value]


def _default_label(raw: Any) -> str:
    status = _status(raw)
    if status == "supported":
        return "Supported"
    if status == "partial":
        return "Partial"
    return "Coming soon"
