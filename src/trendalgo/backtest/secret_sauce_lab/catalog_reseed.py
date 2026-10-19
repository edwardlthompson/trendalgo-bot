"""Peer-inspired cross seeds — mutate neighborhood, never exact catalog clones."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct

_BH = "B&H"
_ORACLE = "Oracle max"
_SS = "Secret Sauce Lab"
_SS_ALIASES = frozenset({"Secret Sauce", "Secret Sauce Lab", "Secret Sauce TA"})
_BOUNDED = "bounded_reversal"

# Level offsets so Sauce never ships peer's exact 30/70 (or whatever) alone.
_LEVEL_SHIFTS = (-10, -5, 5, 10)
_EXTRA_GATES = (
    (("above_sma50", ">=", 1.0),),
    (("above_sma20", ">=", 1.0),),
    (("vol_z", ">=", 0.5),),
)


def peer_hints_from_rows(
    rows: list[dict[str, Any]],
    *,
    preferred_tf: str = "1h",
    prefer_osc: bool = True,
    require_beat_bh: bool = True,
) -> list[dict[str, Any]]:
    """Top beaters. Clearance uses absolute sort; inspire may prefer osc/BR first."""
    from trendalgo.ta.signal_kinds import oscillator_levels, signal_kind

    bh = _best_bh(rows, preferred_tf)
    peers: list[dict[str, Any]] = []
    for r in rows:
        name = str(r.get("indicator") or "")
        if name in {_BH, _ORACLE, *_SS_ALIASES}:
            continue
        if preferred_tf and str(r.get("timeframe") or "") != preferred_tf:
            continue
        net = float(r.get("net_pct") or float("-inf"))
        if require_beat_bh and net <= bh:
            continue
        raw_params = r.get("params")
        params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
        sid = str(r.get("strategy_id") or name)
        kind = str(params.get("kind") or r.get("kind") or signal_kind(sid))
        el_def, xl_def = oscillator_levels(sid)
        peers.append(
            {
                "indicator": name,
                "net_pct": net,
                "kind": kind,
                "entry_level": _float_param(params, "entry_level", float(el_def)),
                "exit_level": _float_param(params, "exit_level", float(xl_def)),
                "period": int(
                    _float_param(params, "timeperiod", _float_param(params, "length", 14.0))
                ),
                "timeframe": str(r.get("timeframe") or preferred_tf or ""),
            }
        )
    peers.sort(key=lambda p: float(p["net_pct"]), reverse=True)
    if prefer_osc:
        br = [p for p in peers if p["kind"] == _BOUNDED or _looks_oscillator(p["indicator"])]
        rest = [p for p in peers if p not in br]
        return (br + rest)[:8]
    return peers[:8]


def absolute_max_peer_net(rows: list[dict[str, Any]], *, preferred_tf: str = "") -> float | None:
    """Max catalog Net % (any kind) — same bar as Results #2 / smoke."""
    hints = peer_hints_from_rows(
        rows, preferred_tf=preferred_tf, prefer_osc=False, require_beat_bh=False
    )
    # Still ignore rows that aren't real peers (already filtered Oracle/SS/BH).
    if not hints:
        return None
    return float(hints[0]["net_pct"])


def max_peer_net(rows: list[dict[str, Any]], *, preferred_tf: str = "1h") -> float | None:
    """Absolute max peer Net % (not BR-preferred). Prefer empty TF = all frames."""
    return absolute_max_peer_net(rows, preferred_tf=preferred_tf)


def is_rsx_like_hint(hint: dict[str, Any]) -> bool:
    kind = str(hint.get("kind") or "")
    name = str(hint.get("indicator") or "")
    if kind == _BOUNDED or _looks_oscillator(name):
        return True
    return "RSX" in name.upper() or "RSI" in name.upper()


def inspire_cross_seeds(
    strategy_id: str,
    hints: list[dict[str, Any]],
) -> list[tuple[CompositeRule, CompositeRule, str]]:
    """Emit mutated cross seeds near peer levels; exclude exact peer clones."""
    out: list[tuple[CompositeRule, CompositeRule, str]] = []
    seen: set[tuple[str, ...]] = set()
    for hint in hints:
        el0, xl0 = _rsi_like_levels(float(hint["entry_level"]), float(hint["exit_level"]))
        # Exact clone signatures to reject (RSI-only and stoch-only at peer levels).
        reject = {
            _sig((f"rsi_xup_{el0}",), (f"rsi_xdn_{xl0}",)),
            _sig((f"stoch_xup_{el0}",), (f"stoch_xdn_{xl0}",)),
        }
        candidates = _mutants_around(strategy_id, el0, xl0)
        for er, xr in candidates:
            key = _sig_rules(er, xr)
            if key in reject or key in seen:
                continue
            seen.add(key)
            out.append((er, xr, "peer_inspire"))
    return out


def is_exact_peer_clone(
    entry: CompositeRule,
    exit_rule: CompositeRule,
    hints: list[dict[str, Any]],
) -> bool:
    """True if entry/exit is a lone rsi/stoch cross at a peer's exact levels."""
    efeats = tuple(c.feature for c in entry.conjuncts)
    xfeats = tuple(c.feature for c in exit_rule.conjuncts)
    if len(efeats) != 1 or len(xfeats) != 1:
        return False
    for hint in hints:
        el0, xl0 = _rsi_like_levels(float(hint["entry_level"]), float(hint["exit_level"]))
        if efeats[0] == f"rsi_xup_{el0}" and xfeats[0] == f"rsi_xdn_{xl0}":
            return True
        if efeats[0] == f"stoch_xup_{el0}" and xfeats[0] == f"stoch_xdn_{xl0}":
            return True
    return False


def _rsi_like_levels(entry: float, exit_: float) -> tuple[int, int]:
    """Map peer levels into RSI/stoch-like 0–100 band for cross features."""
    el = int(round(entry))
    xl = int(round(exit_))
    # Non-0–100 oscillators (WILLR, CCI, …) → default RSX-like neighborhood.
    if el < 5 or el > 50 or xl < 50 or xl > 95 or el >= xl:
        return 30, 70
    return el, xl


def _mutants_around(sid: str, el0: int, xl0: int) -> list[tuple[CompositeRule, CompositeRule]]:
    pairs: list[tuple[CompositeRule, CompositeRule]] = []
    entry_levels = {el0 + d for d in _LEVEL_SHIFTS}
    exit_levels = {xl0 + d for d in _LEVEL_SHIFTS}
    # Also try alternate oscillator at shifted levels.
    for el in sorted(entry_levels):
        for xl in sorted(exit_levels):
            if el < 10 or el > 45 or xl < 55 or xl > 90 or el >= xl:
                continue
            # Skip exact peer levels for RSI-only (clone reject handled upstream too).
            rsi_e, rsi_x = f"rsi_xup_{el}", f"rsi_xdn_{xl}"
            stoch_e = f"stoch_xup_{20 if el <= 22 else 25}"
            stoch_x = f"stoch_xdn_{80 if xl >= 78 else 75}"
            pairs.append(_pair(sid, ((rsi_e, ">=", 1.0),), ((rsi_x, ">=", 1.0),)))
            for gate in _EXTRA_GATES:
                pairs.append(_pair(sid, ((rsi_e, ">=", 1.0),) + gate, ((rsi_x, ">=", 1.0),)))
            pairs.append(_pair(sid, ((stoch_e, ">=", 1.0),), ((stoch_x, ">=", 1.0),)))
            pairs.append(
                _pair(
                    sid, ((stoch_e, ">=", 1.0), ("above_sma20", ">=", 1.0)), ((stoch_x, ">=", 1.0),)
                )
            )
    return pairs


def _pair(
    sid: str,
    entry: tuple[tuple[str, str, float], ...],
    exit_: tuple[tuple[str, str, float], ...],
) -> tuple[CompositeRule, CompositeRule]:
    er = CompositeRule(
        strategy_id=sid,
        conjuncts=tuple(RuleConjunct(feature=f, op=o, value=float(v)) for f, o, v in entry),
        rationale="peer-inspired entry",
    )
    xr = CompositeRule(
        strategy_id=sid,
        conjuncts=tuple(RuleConjunct(feature=f, op=o, value=float(v)) for f, o, v in exit_),
        rationale="peer-inspired exit",
    )
    return er, xr


def _sig(entry_feats: tuple[str, ...], exit_feats: tuple[str, ...]) -> tuple[str, ...]:
    return entry_feats + ("|",) + exit_feats


def _sig_rules(er: CompositeRule, xr: CompositeRule) -> tuple[str, ...]:
    return tuple(c.feature for c in er.conjuncts) + ("|",) + tuple(c.feature for c in xr.conjuncts)


def _best_bh(rows: list[dict[str, Any]], preferred_tf: str) -> float:
    best = float("-inf")
    for r in rows:
        if str(r.get("indicator") or "") != _BH:
            continue
        if preferred_tf and str(r.get("timeframe") or "") not in {"", preferred_tf}:
            continue
        best = max(best, float(r.get("net_pct") or float("-inf")))
    return best if best != float("-inf") else 0.0


def _float_param(params: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(params.get(key, default))
    except (TypeError, ValueError):
        return default


def _looks_oscillator(name: str) -> bool:
    u = name.upper()
    return any(tok in u for tok in ("RSI", "RSX", "STOCH", "MFI", "WILLR", "CCI", "CMO"))
