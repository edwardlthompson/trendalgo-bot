"""Content-aware Settings grid: measure → pack tight (fill gaps, push on grow)."""

from __future__ import annotations

import math

from trendalgo.device.portfolio_grid_snap import Rect, overlaps
from trendalgo.device.portfolio_layout_prefs import Placement


def rows_for_pixels(height_px: int, cell_h: float, gap_px: int) -> int:
    """Grid rows needed so pixel height fits without clipping."""
    step = float(cell_h) + float(gap_px)
    if step <= 0:
        return 1
    return max(1, int(math.ceil((max(1, height_px) + gap_px) / step)))


def cols_for_pixels(width_px: int, cell_w: float, gap_px: int, *, cols: int) -> int:
    """Grid columns needed so pixel width fits labels/fields without clipping."""
    step = float(cell_w) + float(gap_px)
    if step <= 0:
        return 1
    need = max(1, int(math.ceil((max(1, width_px) + gap_px) / step)))
    return max(1, min(cols, need))


def reflow_content_heights(
    placements: list[Placement],
    height_rows: dict[str, int],
    *,
    cols: int,
    pin_id: str | None = None,
    width_cols: dict[str, int] | None = None,
) -> list[Placement]:
    """Apply content w/h and pack into a non-overlapping, gap-free layout.

    Modules prefer their column; width/height grow to content. Rows pack top-down
    so growth pushes neighbors and collapse/DnD fills holes. ``pin_id`` (after
    drag) is placed first at its drop cell.
    """
    cols = max(1, cols)
    widths = width_cols or {}
    by_id: dict[str, Placement] = {}
    for p in placements:
        w = max(1, min(int(widths.get(p.id, p.w)), cols))
        col = max(0, min(p.col, cols - w))
        by_id[p.id] = Placement(
            id=p.id,
            col=col,
            row=max(0, p.row),
            w=w,
            h=max(1, int(height_rows.get(p.id, p.h))),
        )

    ordered: list[Placement] = []
    if pin_id is not None and pin_id in by_id:
        ordered.append(by_id[pin_id])
    ordered.extend(
        sorted(
            (p for p in by_id.values() if p.id != pin_id),
            key=lambda p: (p.row, p.col, p.id),
        )
    )

    placed: list[Placement] = []
    for p in ordered:
        if pin_id is not None and p.id == pin_id and not placed:
            trial = Placement(id=p.id, col=p.col, row=p.row, w=p.w, h=p.h)
            if not _hits(trial, placed):
                placed.append(trial)
                continue
        col, row = _first_fit_cell(placed, col=p.col, w=p.w, h=p.h, cols=cols)
        placed.append(Placement(id=p.id, col=col, row=row, w=p.w, h=p.h))
    return placed


def _first_fit_cell(
    occupied: list[Placement],
    *,
    col: int,
    w: int,
    h: int,
    cols: int,
) -> tuple[int, int]:
    """Lowest row at preferred col; else first free cell elsewhere."""
    w = max(1, min(w, cols))
    col = max(0, min(col, cols - w))
    for row in range(0, 512):
        trial = Rect(col, row, w, h)
        if not any(overlaps(trial, Rect(o.col, o.row, o.w, o.h)) for o in occupied):
            return col, row
    for alt_col in range(0, cols - w + 1):
        for row in range(0, 512):
            trial = Rect(alt_col, row, w, h)
            if not any(overlaps(trial, Rect(o.col, o.row, o.w, o.h)) for o in occupied):
                return alt_col, row
    return col, 512


def _hits(trial: Placement, others: list[Placement]) -> bool:
    a = Rect(trial.col, trial.row, trial.w, trial.h)
    return any(overlaps(a, Rect(o.col, o.row, o.w, o.h)) for o in others)
