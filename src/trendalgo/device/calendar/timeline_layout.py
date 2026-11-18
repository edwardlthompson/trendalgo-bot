"""Pure layout helpers for event markers / callout packing on a timeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class TimelineMarker:
    index: int  # 1-based display number
    day: date
    title: str
    displayed_date: str
    is_estimated: bool
    url: str
    show_callout: bool


def pack_callouts(
    markers: list[tuple[date, str, str, bool, str]],
    *,
    min_gap_days: float = 3.0,
) -> list[TimelineMarker]:
    """Number events and enable title bubbles when neighbors are far enough apart."""
    if not markers:
        return []
    ordered = sorted(markers, key=lambda m: m[0])
    out: list[TimelineMarker] = []
    last_callout_day: date | None = None
    for i, (day, title, displayed, estimated, url) in enumerate(ordered, start=1):
        show = True
        if last_callout_day is not None:
            gap = abs((day - last_callout_day).days)
            if gap < min_gap_days:
                show = False
        if show:
            last_callout_day = day
        out.append(
            TimelineMarker(
                index=i,
                day=day,
                title=title,
                displayed_date=displayed,
                is_estimated=estimated,
                url=url,
                show_callout=show,
            )
        )
    return out


def day_to_ms(day: date) -> int:
    return int(datetime(day.year, day.month, day.day).timestamp() * 1000)
