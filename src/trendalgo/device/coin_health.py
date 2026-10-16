"""Coin Health composite (0–100). Device approximation of snapshot health_score."""

from __future__ import annotations

from typing import Any


def compute_coin_health(coin: dict[str, Any]) -> float:
    """Blend uniformity, 7d gain, volume acceleration, and risk into a 0–100 score."""
    uni = _clamp(_as_float(coin.get("uniformity_score")), 0.0, 100.0)
    if uni is None:
        uni = 50.0
    gain7 = _pct_to_score(_gain7(coin))
    vol = _pct_to_score(_as_float(coin.get("volume_acceleration_pct")))
    risk = _risk_score(coin)
    score = 0.45 * uni + 0.25 * gain7 + 0.15 * vol + 0.15 * risk
    clamped = _clamp(score, 0.0, 100.0)
    return round(0.0 if clamped is None else clamped, 2)


def _gain7(coin: dict[str, Any]) -> float | None:
    gains = coin.get("gains")
    if isinstance(gains, dict):
        return _as_float(gains.get("7d"))
    return None


def _risk_score(coin: dict[str, Any]) -> float:
    """Lower HV and shallower drawdown → higher score. Defaults to neutral 50."""
    hv = _as_float(coin.get("hv_7d_pct"))
    dd = _as_float(coin.get("max_drawdown_pct"))
    risk = coin.get("risk_context")
    if isinstance(risk, dict):
        if hv is None:
            hv = _as_float(risk.get("hv_7d_annualized_pct"))
        if dd is None:
            dd = _as_float(risk.get("max_drawdown_30d_pct"))
    parts: list[float] = []
    if hv is not None:
        # HV ~0 → 100; HV ≥100 → 0
        parts.append(100.0 - (_clamp(hv, 0.0, 100.0) or 0.0))
    if dd is not None:
        # DD is negative; -5 → high, -80 → low
        depth = abs(dd)
        parts.append(100.0 - (_clamp(depth, 0.0, 100.0) or 0.0))
    if not parts:
        return 50.0
    return sum(parts) / len(parts)


def _pct_to_score(raw: float | None) -> float:
    """Map about -50..+50 percent into 0..100."""
    if raw is None:
        return 50.0
    mapped = _clamp((raw + 50.0) / 100.0 * 100.0, 0.0, 100.0)
    return 50.0 if mapped is None else mapped


def _as_float(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _clamp(value: float | None, low: float, high: float) -> float | None:
    if value is None:
        return None
    return max(low, min(high, value))
