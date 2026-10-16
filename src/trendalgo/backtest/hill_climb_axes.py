"""Integer-only hill-climb axes for every TA strategy."""

from __future__ import annotations

import math
from typing import Any

from trendalgo.ta.param_specs import ta_param_specs
from trendalgo.ta.signals import signal_kind

_LEVEL_AXES: tuple[tuple[str, int, int, int], ...] = (
    ("entry_level", 30, 5, 50),
    ("exit_level", 70, 50, 95),
)


def seed_params(strategy_id: str, seed_params_raw: dict[str, Any] | None) -> dict[str, Any]:
    """Merge defaults, specs, and signal-level keys; coerce every setting to int."""
    from trendalgo.backtest.ta_fleet import default_params

    params = dict(seed_params_raw or default_params(strategy_id))
    for spec in ta_param_specs(strategy_id):
        params.setdefault(str(spec.key), spec.default)
    kind = signal_kind(strategy_id)
    if kind == "bounded_reversal":
        for key, default, _lo, _hi in _LEVEL_AXES:
            params.setdefault(key, default)
    if kind == "ma_cross":
        params.setdefault("fast", 10)
        params.setdefault("slow", 30)
    return int_params(params, strategy_id)


def int_params(params: dict[str, Any], strategy_id: str = "") -> dict[str, Any]:
    """Round every numeric setting to an int inside its axis bounds."""
    bounds = {key: (lo, hi) for key, _step, lo, hi, _as_int in climb_axes(strategy_id, params)}
    out: dict[str, Any] = {}
    for key, value in params.items():
        if not _is_number(value):
            out[key] = value
            continue
        rounded = int(round(float(value)))
        if key in bounds:
            lo, hi = bounds[key]
            rounded = max(int(lo), min(int(hi), rounded))
        out[key] = rounded
    return out


def climb_axes(
    strategy_id: str, params: dict[str, Any]
) -> list[tuple[str, float, float, float, bool]]:
    """Every optimizable axis as integer steps of 1."""
    out: list[tuple[str, float, float, float, bool]] = []
    seen: set[str] = set()
    for spec in ta_param_specs(strategy_id):
        key = str(spec.key)
        lo = float(spec.min if spec.min is not None else spec.default)
        hi = float(spec.max if spec.max is not None else spec.default)
        out.append(_axis_row(key, lo, hi))
        seen.add(key)
    if signal_kind(strategy_id) == "bounded_reversal":
        for key, _default, lo, hi in _LEVEL_AXES:
            if key in seen:
                continue
            out.append(_axis_row(key, float(lo), float(hi)))
            seen.add(key)
    for key, value in params.items():
        if key in seen or not _is_number(value):
            continue
        lo, hi = _infer_bounds(key, float(value))
        out.append(_axis_row(key, lo, hi))
        seen.add(key)
    return out


def step_value(
    current: Any, delta: float, lo: float, hi: float, *, as_int: bool
) -> float | int | None:
    try:
        base = float(current)
    except (TypeError, ValueError):
        return None
    nxt = base + delta
    if nxt < lo or nxt > hi:
        return None
    if as_int:
        return int(round(nxt))
    return round(nxt, 4)


def _axis_row(key: str, lo: float, hi: float) -> tuple[str, float, float, float, bool]:
    # Integer-only policy: always step by 1 inside inclusive int bounds.
    lo_i = int(lo) if float(lo).is_integer() else int(math.ceil(lo))
    hi_i = int(hi) if float(hi).is_integer() else int(math.floor(hi))
    if hi_i < lo_i:
        lo_i, hi_i = hi_i, lo_i
    return (key, 1.0, float(lo_i), float(hi_i), True)


def _infer_bounds(key: str, value: float) -> tuple[float, float]:
    lower = key.casefold()
    if "entry" in lower:
        return 5.0, 50.0
    if "exit" in lower:
        return 50.0, 95.0
    if any(token in lower for token in ("period", "length", "fast", "slow", "signal")):
        return 2.0, 200.0
    if "dev" in lower or "mult" in lower:
        return 1.0, 5.0
    span = max(abs(value) * 0.5, 5.0)
    return max(1.0, value - span), value + span


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
