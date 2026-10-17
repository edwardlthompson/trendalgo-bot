"""Pack Dashboard placements into a non-overlapping grid."""

from __future__ import annotations

from trendalgo.device.portfolio_grid_snap import Rect, overlaps
from trendalgo.device.portfolio_layout_prefs import Placement
from trendalgo.device.portfolio_module_catalog import spec_for


def pack_placements(
    wanted_ids: list[str],
    *,
    existing: list[Placement] | None = None,
    cols: int = 24,
) -> list[Placement]:
    """Keep existing rects for still-wanted ids; place new ids in free cells."""
    existing = existing or []
    keep = {p.id: p for p in existing if p.id in wanted_ids}
    out: list[Placement] = []
    occupied: list[Rect] = []
    for mid in wanted_ids:
        if mid in keep:
            p = keep[mid]
            out.append(p)
            occupied.append(Rect(p.col, p.row, p.w, p.h))
    for mid in wanted_ids:
        if mid in keep:
            continue
        meta = spec_for(mid)
        w = meta.default_w if meta else 4
        h = meta.default_h if meta else 3
        w = min(w, cols)
        slot = _first_fit(occupied, cols=cols, w=w, h=h)
        out.append(Placement(id=mid, col=slot.col, row=slot.row, w=w, h=h))
        occupied.append(slot)
    return out


def required_rows(placements: list[Placement], *, minimum: int = 12) -> int:
    bottom = max((p.row + p.h for p in placements), default=0)
    return max(minimum, bottom)


def _first_fit(occupied: list[Rect], *, cols: int, w: int, h: int) -> Rect:
    row = 0
    while True:
        for col in range(0, max(1, cols - w + 1)):
            trial = Rect(col, row, w, h)
            if not any(overlaps(trial, other) for other in occupied):
                return trial
        row += 1
        if row > 500:
            return Rect(0, row, w, h)
