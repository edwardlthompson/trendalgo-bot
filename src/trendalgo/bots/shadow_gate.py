"""Mandatory shadow gate before go-live (Phase 0 / 5)."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MIN_DAYS = 3
DEFAULT_MIN_SIGNALS = 20


@dataclass(frozen=True)
class ShadowProgress:
    days: float
    signals: int
    min_days: float = DEFAULT_MIN_DAYS
    min_signals: int = DEFAULT_MIN_SIGNALS

    @property
    def passed(self) -> bool:
        return self.days >= self.min_days or self.signals >= self.min_signals

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "days": self.days,
            "signals": self.signals,
            "min_days": self.min_days,
            "min_signals": self.min_signals,
            "passed": self.passed,
        }


def shadow_gate_allows_go_live(
    progress: ShadowProgress, *, typed_override: str | None = None
) -> tuple[bool, str]:
    """Go-live stays blocked until shadow passes, unless typed override is exact."""
    if progress.passed:
        return True, "shadow_ok"
    if typed_override == "I ACCEPT EARLY GO-LIVE":
        return True, "typed_override"
    return False, "shadow_incomplete"
