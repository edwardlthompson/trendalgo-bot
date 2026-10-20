"""Hill-climb axes for every TA strategy (oscillator-aware entry/exit levels)."""

from __future__ import annotations

import math
from typing import Any

from trendalgo.ta.param_specs import ta_param_specs
from trendalgo.ta.signal_kinds import oscillator_levels, signal_kind


def seed_params(strategy_id: str, seed_params_raw: dict[str, Any] | None) -> dict[str, Any]:
    """Merge defaults, specs, and oscillator levels; coerce numbers to climb types."""
    from trendalgo.backtest.ta_fleet import default_params

    params = dict(seed_params_raw or default_params(strategy_id))
    for spec in ta_param_specs(strategy_id):
        params.setdefault(str(spec.key), spec.default)
    kind = signal_kind(strategy_id)
    if kind == "bounded_reversal":
        entry, exit_ = oscillator_levels(strategy_id)
        # Never inject RSI 30/70 onto WILLR/CTI/FISHER/etc.
        params.setdefault("entry_level", entry)
        params.setdefault("exit_level", exit_)
        params = _sanitize_osc_levels(strategy_id, params)
    if kind == "ma_cross":
        params.setdefault("fast", 10)
        params.setdefault("slow", 30)
    return int_params(params, strategy_id)


def int_params(params: dict[str, Any], strategy_id: str = "") -> dict[str, Any]:
    """Clamp numeric settings to climb axes (ints, or floats for fractional oscillators)."""
    cleaned = dict(params)
    if strategy_id and signal_kind(strategy_id) == "bounded_reversal":
        cleaned = _sanitize_osc_levels(strategy_id, cleaned)
    axes = {
        key: (step, lo, hi, as_int)
        for key, step, lo, hi, as_int in climb_axes(strategy_id, cleaned)
    }
    out: dict[str, Any] = {}
    for key, value in cleaned.items():
        if not _is_number(value):
            out[key] = value
            continue
        number = float(value)
        if key in axes:
            step, lo, hi, as_int = axes[key]
            number = max(lo, min(hi, number))
            if as_int:
                out[key] = int(round(number))
            else:
                # Snap to step grid for fractional oscillators (CTI / FISHER).
                if step > 0:
                    number = round(round(number / step) * step, 6)
                out[key] = float(number)
            continue
        out[key] = int(round(number))
    return out


def climb_axes(
    strategy_id: str, params: dict[str, Any]
) -> list[tuple[str, float, float, float, bool]]:
    """Every optimizable axis as (key, step, lo, hi, as_int)."""
    out: list[tuple[str, float, float, float, bool]] = []
    seen: set[str] = set()
    for spec in ta_param_specs(strategy_id):
        key = str(spec.key)
        lo = float(spec.min if spec.min is not None else spec.default)
        hi = float(spec.max if spec.max is not None else spec.default)
        out.append(_axis_row(key, lo, hi, as_int=True))
        seen.add(key)
    if signal_kind(strategy_id) == "bounded_reversal":
        for key, step, lo, hi, as_int in _oscillator_level_axes(strategy_id):
            if key in seen:
                continue
            out.append((key, step, lo, hi, as_int))
            seen.add(key)
    for key, value in params.items():
        if key in seen or not _is_number(value):
            continue
        lo, hi = _infer_bounds(key, float(value))
        out.append(_axis_row(key, lo, hi, as_int=True))
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


def _sanitize_osc_levels(strategy_id: str, params: dict[str, Any]) -> dict[str, Any]:
    """Replace RSI-style 30/70 when they are illegal for this oscillator's range."""
    entry_d, exit_d = oscillator_levels(strategy_id)
    out = dict(params)
    try:
        entry = float(out.get("entry_level", entry_d))
        exit_ = float(out.get("exit_level", exit_d))
    except (TypeError, ValueError):
        out["entry_level"] = entry_d
        out["exit_level"] = exit_d
        return out
    # WILLR/CCI-style (entry default < 0): positive RSI levels are always wrong.
    if entry_d < 0 and entry > 0:
        out["entry_level"] = entry_d
        out["exit_level"] = exit_d
        return out
    # Fractional oscillators: RSI ints 30/70 are wrong.
    if not float(entry_d).is_integer() and (abs(entry) >= 5 or abs(exit_) >= 5):
        out["entry_level"] = entry_d
        out["exit_level"] = exit_d
    return out


def _oscillator_level_axes(
    strategy_id: str,
) -> list[tuple[str, float, float, float, bool]]:
    entry, exit_ = oscillator_levels(strategy_id)
    as_int = float(entry).is_integer() and float(exit_).is_integer()
    if not as_int:
        # CTI / FISHER — small fractional grid around catalog defaults.
        span = max(abs(entry), abs(exit_), 0.5) + 0.5
        return [
            ("entry_level", 0.1, -span, 0.0, False),
            ("exit_level", 0.1, 0.0, span, False),
        ]
    if entry < 0 and exit_ <= 0:
        # WILLR ∈ [-100, 0]
        return [
            ("entry_level", 1.0, -100.0, -10.0, True),
            ("exit_level", 1.0, -90.0, 0.0, True),
        ]
    if entry < 0 < exit_:
        # CCI / CMO / SMI style
        pad = max(abs(entry), abs(exit_), 50.0)
        return [
            ("entry_level", 1.0, -pad, -1.0, True),
            ("exit_level", 1.0, 1.0, pad, True),
        ]
    # RSI / MFI / QQE style 0–100
    return [
        ("entry_level", 1.0, 5.0, 50.0, True),
        ("exit_level", 1.0, 50.0, 95.0, True),
    ]


def _axis_row(
    key: str, lo: float, hi: float, *, as_int: bool
) -> tuple[str, float, float, float, bool]:
    if as_int:
        lo_i = int(lo) if float(lo).is_integer() else int(math.ceil(lo))
        hi_i = int(hi) if float(hi).is_integer() else int(math.floor(hi))
        if hi_i < lo_i:
            lo_i, hi_i = hi_i, lo_i
        return (key, 1.0, float(lo_i), float(hi_i), True)
    if hi < lo:
        lo, hi = hi, lo
    return (key, 0.1, float(lo), float(hi), False)


def _infer_bounds(key: str, value: float) -> tuple[float, float]:
    lower = key.casefold()
    if "entry" in lower:
        if value < 0:
            return -100.0, -1.0
        return 5.0, 50.0
    if "exit" in lower:
        if value <= 0:
            return -90.0, 0.0
        return 50.0, 95.0
    if any(token in lower for token in ("period", "length", "fast", "slow", "signal")):
        return 2.0, 200.0
    if "dev" in lower or "mult" in lower:
        return 1.0, 5.0
    span = max(abs(value) * 0.5, 5.0)
    return max(1.0, value - span), value + span


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
