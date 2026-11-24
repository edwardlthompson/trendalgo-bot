"""Scan progress surface with ETA + pair glance (AV-G-STR9)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.backtest_scan_eta import format_remaining, remaining_seconds
from trendalgo.device.scan_progress import progress_file_name, read_progress


def _load_backtest_progress(root: Path) -> dict[str, Any]:
    from trendalgo.device.pair_scan_progress import PROGRESS_FILE, read_progress

    raw = read_progress(root) or {}
    phase = str(raw.get("phase") or "").strip()
    done = _as_int(raw.get("done"), 0)
    total = _as_int(raw.get("total"), 0)
    pair = _format_pair_label(str(raw.get("current_pair") or ""))
    events = [str(x) for x in (raw.get("events") or []) if str(x).strip()]
    msg = str(raw.get("message") or "").strip()
    if msg and (not events or events[-1] != msg):
        events.append(msg)
    pct = max(0.0, min(100.0, 100.0 * done / total)) if total > 0 else 0.0
    eta_s = raw.get("eta_remaining_s")
    try:
        eta_label = format_remaining(float(eta_s)) if eta_s is not None else "—"
    except (TypeError, ValueError):
        eta_label = "—"
    busy = bool(phase and phase not in {"done", "error", "cancelled"})
    pairs_done = _as_int(raw.get("pairs_done"), 1 if phase == "done" else 0)
    pairs_total = _as_int(raw.get("pairs_total"), 1 if pair != "—" else 0)
    return {
        "lane": "backtest",
        "phase": phase or (msg or "Idle"),
        "busy": busy,
        "file": PROGRESS_FILE,
        "lines": events[-120:],
        "raw_keys": sorted(str(k) for k in raw),
        "percent": pct,
        "current_pair": pair,
        "pairs_label": f"Single-pair backtest ({pairs_done}/{max(1, pairs_total)})"
        if pair != "—"
        else "Single-pair backtest",
        "eta_label": eta_label,
        "done": done,
        "total": total,
    }


def load_progress_surface(root: Path, *, lane: str = "crypto") -> dict[str, Any]:
    if (lane or "").strip().lower() == "backtest":
        return _load_backtest_progress(root)
    raw = read_progress(root, lane=lane) or {}
    state_raw = raw.get("state")
    state: dict[str, Any] = state_raw if isinstance(state_raw, dict) else {}
    # Prefer live phase from state — never let the last log error replace the header.
    phase = str(
        state.get("phase") or raw.get("phase") or state.get("label") or raw.get("label") or ""
    ).strip()
    raw_events = raw.get("events")
    events: list[Any] = list(raw_events) if isinstance(raw_events, list) else []
    lines: list[str] = []
    for ev in events[-80:]:
        if isinstance(ev, dict):
            lines.append(str(ev.get("message") or ev.get("text") or ""))
        else:
            lines.append(str(ev))
    done = _as_int(raw.get("done"), _as_int(state.get("step_done"), 0))
    total = _as_int(raw.get("total"), _as_int(state.get("step_total"), 0))
    current = raw.get("current_pair")
    if current is None:
        current = state.get("current_pair")
    pair = _format_pair_label(str(current) if current is not None else None)
    pairs_done = _as_int_opt(raw.get("pairs_done"), _as_int_opt(state.get("pairs_done"), None))
    pairs_total = _as_int_opt(raw.get("pairs_total"), _as_int_opt(state.get("pairs_total"), None))
    elapsed = float(raw.get("elapsed_s") or state.get("elapsed_s") or raw.get("elapsed") or 0.0)
    stamped = raw.get("remaining_s")
    try:
        stamped_f = float(stamped) if stamped is not None else None
    except (TypeError, ValueError):
        stamped_f = None
    prior = float(raw.get("prior_s") or 0.0)
    snap = remaining_seconds(
        elapsed_s=elapsed,
        done=done,
        total=total,
        prior_s=prior,
        stamped_remaining_s=stamped_f,
    )
    pct = 0.0
    if total > 0:
        pct = max(0.0, min(100.0, 100.0 * done / total))
    elif raw.get("percent") is not None:
        try:
            pct = float(raw["percent"])
        except (TypeError, ValueError, KeyError):
            pct = 0.0
    busy = bool(
        raw.get("busy")
        or raw.get("running")
        or state.get("active")
        or str(state.get("status") or "") == "running"
        or phase
    )
    message = str(raw.get("message") or "").strip()
    header = phase or ("Scanning…" if busy else (message or "Idle"))
    return {
        "lane": lane,
        "phase": header,
        "busy": busy,
        "file": progress_file_name(lane),
        "lines": [ln for ln in lines if ln],
        "raw_keys": sorted(str(k) for k in raw),
        "percent": pct,
        "current_pair": pair,
        "pairs_label": _pairs_remaining_label(pairs_done, pairs_total),
        "eta_label": format_remaining(snap.remaining_s) if snap.remaining_s is not None else "—",
        "done": done,
        "total": total,
    }


def _format_pair_label(raw: str | None) -> str:
    text = str(raw or "").strip()
    if not text or text in {"?", "—", "-"}:
        return "—"
    if "/" in text:
        return text.upper()
    return f"{text.upper()}/USD"


def _pairs_remaining_label(done: int | None, total: int | None) -> str:
    if total is None or int(total) <= 0:
        return "Pairs remaining: —"
    done_n = max(0, int(done or 0))
    total_n = max(0, int(total))
    remaining = max(0, total_n - done_n)
    return f"{remaining} pairs left ({done_n}/{total_n})"


def _as_int(raw: object, fallback: int) -> int:
    if raw is None:
        return fallback
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return fallback


def _as_int_opt(raw: object, fallback: int | None) -> int | None:
    if raw is None:
        return fallback
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return fallback
