"""Study UI honesty helpers — separate re-fit Net% from live (LIVE-05)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StudyNetView:
    refit_label: str
    live_label: str
    disclaimer: str

    def as_lines(self) -> list[str]:
        return [self.refit_label, self.live_label, self.disclaimer]


def separate_study_nets(*, refit_net_pct: float, live_net_pct: float | None) -> StudyNetView:
    """Keep retuned Net % visually separate from live realized Net %."""
    live = "—" if live_net_pct is None else f"{float(live_net_pct):.2f}%"
    return StudyNetView(
        refit_label=f"Re-fit Net % (study only): {float(refit_net_pct):.2f}%",
        live_label=f"Live realized Net %: {live}",
        disclaimer="Re-fit Net % is not a track record.",
    )


def format_param_diff(
    *,
    old: dict[str, Any],
    new: dict[str, Any],
    regime_axis: str,
    holdout_evidence: dict[str, Any],
) -> str:
    """Show what changed, which regime axis triggered it, and holdout evidence."""
    bits: list[str] = []
    keys = sorted(set(old) | set(new))
    for key in keys:
        ov, nv = old.get(key), new.get(key)
        if ov != nv:
            bits.append(f"{key}: {ov} → {nv}")
    diff = "; ".join(bits) if bits else "no param change"
    inc = holdout_evidence.get("incumbent")
    cand = holdout_evidence.get("candidate")
    margin = holdout_evidence.get("margin")
    return (
        f"Diff — {diff} · regime axis {regime_axis} · "
        f"holdout incumbent {inc} / candidate {cand} (margin {margin})"
    )
