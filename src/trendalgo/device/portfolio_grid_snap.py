"""Pure snap / magnetism / overlap helpers for the Dashboard grid."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    col: int
    row: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.col + self.w

    @property
    def bottom(self) -> int:
        return self.row + self.h


def cell_size(
    canvas_w: int,
    canvas_h: int,
    cols: int,
    rows: int,
    gap_px: int,
    *,
    fixed_row_px: float = 0.0,
) -> tuple[float, float]:
    """Column width from canvas; square cells unless fixed_row_px > 0 (Settings)."""
    del canvas_h, rows
    cols = max(1, cols)
    gap_x = gap_px * (cols - 1)
    cw = max(1.0, (canvas_w - gap_x) / cols)
    if fixed_row_px > 0:
        return cw, float(fixed_row_px)
    return cw, cw


def rect_to_pixels(
    rect: Rect, cell_w: float, cell_h: float, gap_px: int
) -> tuple[int, int, int, int]:
    x = int(rect.col * (cell_w + gap_px))
    y = int(rect.row * (cell_h + gap_px))
    w = int(rect.w * cell_w + max(0, rect.w - 1) * gap_px)
    h = int(rect.h * cell_h + max(0, rect.h - 1) * gap_px)
    return x, y, w, h


def snap_point(
    x: float,
    y: float,
    *,
    cell_w: float,
    cell_h: float,
    gap_px: int,
    magnet_px: float,
    cols: int,
    rows: int,
    w: int,
    h: int,
) -> Rect:
    """Snap top-left pixel coords to a grid rect with magnetism near grid lines."""
    step_x = cell_w + gap_px
    step_y = cell_h + gap_px
    raw_col = x / step_x if step_x else 0.0
    raw_row = y / step_y if step_y else 0.0
    col = _magnet_axis(raw_col, magnet_px / step_x if step_x else 0.0)
    row = _magnet_axis(raw_row, magnet_px / step_y if step_y else 0.0)
    col = max(0, min(col, max(0, cols - w)))
    row = max(0, min(row, max(0, rows - h)))
    return Rect(col=col, row=row, w=w, h=h)


def overlaps(a: Rect, b: Rect) -> bool:
    return not (a.right <= b.col or b.right <= a.col or a.bottom <= b.row or b.bottom <= a.row)


def snap_resize(
    origin: Rect,
    br_x: float,
    br_y: float,
    *,
    cell_w: float,
    cell_h: float,
    gap_px: int,
    magnet_px: float,
    cols: int,
    rows: int,
    min_w: int,
    min_h: int,
    max_w: int,
    max_h: int,
) -> Rect:
    """Snap bottom-right pixel to a new span; top-left (origin.col/row) stays fixed."""
    step_x = cell_w + gap_px
    step_y = cell_h + gap_px
    # Exclusive right/bottom edge in cell units (like CSS grid line index).
    raw_right = br_x / step_x if step_x else float(origin.col + origin.w)
    raw_bottom = br_y / step_y if step_y else float(origin.row + origin.h)
    right = _magnet_axis(raw_right, magnet_px / step_x if step_x else 0.0)
    bottom = _magnet_axis(raw_bottom, magnet_px / step_y if step_y else 0.0)
    max_span_w = max(1, cols - origin.col)
    max_span_h = max(1, rows - origin.row)
    w = max(min_w, min(max_w, max_span_w, right - origin.col))
    h = max(min_h, min(max_h, max_span_h, bottom - origin.row))
    w = max(min_w, min(w, max_span_w))
    h = max(min_h, min(h, max_span_h))
    return Rect(col=origin.col, row=origin.row, w=w, h=h)


def resize_allowed(
    candidate: Rect,
    occupied: list[tuple[str, Rect]],
    *,
    resizing_id: str,
) -> bool:
    """True when candidate does not overlap any other module."""
    return not any(overlaps(candidate, rect) for mid, rect in occupied if mid != resizing_id)


_ROWS_CAP = 96
_PUSH_ITERS = 64


def push_aside_for_resize(
    resizing_id: str,
    new_rect: Rect,
    occupied: list[tuple[str, Rect]],
    *,
    cols: int,
    rows_cap: int = _ROWS_CAP,
) -> dict[str, Rect]:
    """Place resized module; shift others right if free else down until no overlaps."""
    others = [(mid, rect) for mid, rect in occupied if mid != resizing_id]
    layout = _resolve_push(resizing_id, new_rect, others, cols=cols)
    if max((r.bottom for r in layout.values()), default=0) <= rows_cap:
        return layout
    for h in range(new_rect.h - 1, 0, -1):
        trial = Rect(new_rect.col, new_rect.row, new_rect.w, h)
        trial_layout = _resolve_push(resizing_id, trial, others, cols=cols)
        if max((r.bottom for r in trial_layout.values()), default=0) <= rows_cap:
            return trial_layout
    return layout


def _resolve_push(
    resizing_id: str,
    new_rect: Rect,
    others: list[tuple[str, Rect]],
    *,
    cols: int,
) -> dict[str, Rect]:
    layout: dict[str, Rect] = {mid: rect for mid, rect in others}
    layout[resizing_id] = new_rect
    for _ in range(_PUSH_ITERS):
        collision = _first_collision(layout, resizing_id)
        if collision is None:
            break
        mover_id, blocker = collision
        mover = layout[mover_id]
        right_col = blocker.right
        shifted_right = Rect(right_col, mover.row, mover.w, mover.h)
        if right_col + mover.w <= cols and not _would_overlap(shifted_right, layout, mover_id):
            layout[mover_id] = shifted_right
        else:
            layout[mover_id] = Rect(mover.col, max(mover.row, blocker.bottom), mover.w, mover.h)
    return layout


def _first_collision(layout: dict[str, Rect], resizing_id: str) -> tuple[str, Rect] | None:
    """Return (mover_id, blocker_rect) for the top-left-most overlapping non-resized module."""
    ordered = sorted(layout.items(), key=lambda item: (item[1].row, item[1].col, item[0]))
    for mid, rect in ordered:
        if mid == resizing_id:
            continue
        for other_id, other in ordered:
            if other_id == mid:
                continue
            if overlaps(rect, other):
                if other_id == resizing_id or (other.row, other.col) <= (rect.row, rect.col):
                    return mid, other
                return other_id, rect
    return None


def _would_overlap(trial: Rect, layout: dict[str, Rect], skip_id: str) -> bool:
    return any(overlaps(trial, r) for mid, r in layout.items() if mid != skip_id)


def find_free_or_swap(
    candidate: Rect,
    occupied: list[tuple[str, Rect]],
    *,
    moving_id: str,
    cols: int,
    rows: int,
) -> tuple[Rect, str | None]:
    """Return snapped rect and optional id to swap with. Reject → return original occupied slot."""
    others = [(i, r) for i, r in occupied if i != moving_id]
    if not any(overlaps(candidate, r) for _, r in others):
        return candidate, None
    for dc, dr in _spiral():
        trial = Rect(candidate.col + dc, candidate.row + dr, candidate.w, candidate.h)
        if trial.col < 0 or trial.row < 0 or trial.right > cols or trial.bottom > rows:
            continue
        if not any(overlaps(trial, r) for _, r in others):
            return trial, None
    for oid, orect in others:
        if overlaps(candidate, orect) and orect.w == candidate.w and orect.h == candidate.h:
            return candidate, oid
    origin = next((r for i, r in occupied if i == moving_id), candidate)
    return origin, None


def _magnet_axis(raw: float, threshold: float) -> int:
    nearest = round(raw)
    if abs(raw - nearest) <= max(0.0, threshold):
        return int(nearest)
    return int(raw)


def _spiral() -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = [(0, 0)]
    for radius in range(1, 6):
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if max(abs(dc), abs(dr)) == radius:
                    out.append((dc, dr))
    return out
