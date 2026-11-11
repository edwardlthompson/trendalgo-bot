"""Anti-thrash guards for retune (LIVE-03)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class AntiThrashConfig:
    dwell_days: int = 3
    hysteresis_pct: float = 0.3  # absolute Net % points


@dataclass(frozen=True)
class AntiThrashResult:
    accepted: bool
    params: dict[str, Any]
    reason: str


def _nearest_quantile_index(value: float, ladder: list[float]) -> int:
    return min(range(len(ladder)), key=lambda i: abs(ladder[i] - value))


def clamp_one_quantile_step(
    incumbent: dict[str, Any],
    proposed: dict[str, Any],
    quantiles: dict[str, list[float]],
) -> dict[str, Any]:
    """Max one quantile step per parameter per cycle."""
    out = dict(incumbent)
    for key, ladder in quantiles.items():
        if key not in proposed or not ladder:
            continue
        cur = float(incumbent.get(key, proposed[key]))
        tgt = float(proposed[key])
        i_cur = _nearest_quantile_index(cur, ladder)
        i_tgt = _nearest_quantile_index(tgt, ladder)
        if i_tgt > i_cur:
            out[key] = ladder[min(i_cur + 1, len(ladder) - 1)]
        elif i_tgt < i_cur:
            out[key] = ladder[max(i_cur - 1, 0)]
        else:
            out[key] = ladder[i_cur]
    for key, val in proposed.items():
        if key not in quantiles:
            out[key] = val
    return out


def apply_antithrash(
    *,
    incumbent: dict[str, Any],
    proposed: dict[str, Any],
    incumbent_net: float,
    proposed_net: float,
    last_change_utc: datetime | None,
    now_utc: datetime,
    config: AntiThrashConfig | None = None,
    quantiles: dict[str, list[float]] | None = None,
) -> AntiThrashResult:
    cfg = config or AntiThrashConfig()
    now = now_utc.astimezone(UTC)
    if last_change_utc is not None:
        last = last_change_utc.astimezone(UTC)
        if (now - last) < timedelta(days=cfg.dwell_days):
            return AntiThrashResult(False, dict(incumbent), "dwell")
    if abs(float(proposed_net) - float(incumbent_net)) < cfg.hysteresis_pct:
        return AntiThrashResult(False, dict(incumbent), "hysteresis")
    stepped = clamp_one_quantile_step(incumbent, proposed, quantiles or {})
    return AntiThrashResult(True, stepped, "ok")


def simulate_flat_noise_churn(*, days: int, noise_pct: float, seed: int) -> int:
    """Noisy but flat Net % series: count accepted param changes over ``days``."""
    rng = random.Random(seed)
    cfg = AntiThrashConfig(hysteresis_pct=0.3)
    base = datetime(2026, 1, 1, 6, 0, tzinfo=UTC)
    params: dict[str, Any] = {"q": 0.5}
    ladder = {"q": [0.4, 0.5, 0.6, 0.7]}
    last_change: datetime | None = None
    changes = 0
    incumbent_net = 1.0
    for day in range(days):
        now = base + timedelta(days=day)
        noise = (rng.random() - 0.5) * 2.0 * noise_pct
        proposed_net = incumbent_net + noise
        proposed = {"q": 0.6 if noise > 0 else 0.4}
        result = apply_antithrash(
            incumbent=params,
            proposed=proposed,
            incumbent_net=incumbent_net,
            proposed_net=proposed_net,
            last_change_utc=last_change,
            now_utc=now,
            config=cfg,
            quantiles=ladder,
        )
        if result.accepted:
            changes += 1
            params = dict(result.params)
            last_change = now
    return changes
