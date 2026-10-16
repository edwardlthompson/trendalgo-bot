"""Shadow report: the divergence classes, their counts, and the clean rule (row 21).

A shadow run is clean only when it covers the required number of days and has no divergence of any
class. The owner's rule is at least 14 days of clean shadow divergence before any live order (see
BUILD_PLAN, product brief). The caller passes the day count it measured.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Kind = Literal["signal", "fill", "stop", "data"]
REQUIRED_CLEAN_DAYS = 14


@dataclass(frozen=True)
class Divergence:
    kind: Kind
    at: str
    detail: str


@dataclass(frozen=True)
class ShadowReport:
    days: int
    signal: int
    fill: int
    stop: int
    data: int

    @property
    def total(self) -> int:
        return self.signal + self.fill + self.stop + self.data

    def is_clean(self, required_days: int = REQUIRED_CLEAN_DAYS) -> bool:
        return self.days >= required_days and self.total == 0

    def describe(self) -> str:
        clean = "yes" if self.is_clean() else "no"
        return (
            f"shadow days {self.days} of {REQUIRED_CLEAN_DAYS}; signal {self.signal}, "
            f"fill {self.fill}, stop {self.stop}, data {self.data}; clean: {clean}"
        )


def build_report(divergences: Sequence[Divergence], *, days: int) -> ShadowReport:
    if days < 0:
        raise ValueError("days must be zero or more")
    counts = Counter(item.kind for item in divergences)
    return ShadowReport(
        days=days,
        signal=counts["signal"],
        fill=counts["fill"],
        stop=counts["stop"],
        data=counts["data"],
    )
