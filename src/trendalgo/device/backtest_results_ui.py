"""Backtest results table cells, heat ranks, and indicator labels."""

from __future__ import annotations

from typing import Any

from trendalgo.device.indicator_strength import strength_from_row
from trendalgo.device.lts_scan_model import dash
from trendalgo.device.scanner_heat import rank_hex_colors
from trendalgo.device.scanner_signal_sets import is_three_commas_indicator
from trendalgo.device.trade_counts import open_trades, win_pct, wins_losses

_BH = "B&H"
# Column indices matching BACKTEST_RESULT_HEADERS (Show Chart + Create Bot are widgets).
NET_COL = 3
STRENGTH_COL = 12
SHOW_CHART_COL = 13
CREATE_BOT_COL = 14
# invert=True → lower is greener (fewer fees / open / losses / hits / hit%).
HEAT_COLS: dict[int, tuple[str, bool]] = {
    3: ("net_pct", False),
    4: ("fees_paid", True),
    5: ("open_trades", True),
    6: ("wins", False),
    7: ("losses", True),
    8: ("win_pct", False),
    10: ("tsl_hits", True),
    11: ("tsl_hit_pct", True),
    12: ("strength", False),
}


def indicator_label(indicator: str, *, is_bh: bool) -> str:
    text = str(indicator or "—")
    if is_bh:
        return "B&H  ← buy & hold" if text == _BH else text
    if is_three_commas_indicator(text):
        return f"{text} *"
    return text


def skip_tooltip(row: dict[str, Any]) -> str:
    """Human tip when an All-TA row was tried but did not trade."""
    reason = str(row.get("skip_reason") or "").strip()
    if not reason:
        return ""
    labels = {
        "no_trades": "Tried — no entry signals on this window.",
        "no_pattern": "Tried — candle pattern did not appear.",
        "not_a_strategy": "Math helper — not a tradable strategy.",
        "compute_error": "Tried — indicator compute failed on this window.",
        "missing_backend": (
            "Tried — pandas-ta backend missing (install device extras / rebuild the app)."
        ),
        "insufficient_bars": "Tried — not enough bars after warmup.",
    }
    return labels.get(reason, f"Tried — skipped ({reason}).")


def net_tooltip(row: dict[str, Any], *, is_bh: bool) -> str:
    """Show signal-only baseline next to final Net % when they differ."""
    if is_bh:
        return ""
    parts: list[str] = []
    if bool(row.get("protective_tsl")) or bool(row.get("tsl_breath")):
        parts.append(
            "Protective TSL: lowest safe trail from the 1–20% grid (+1% breath when tied)."
        )
    signal = _as_float(row.get("signal_net_pct"))
    final = _as_float(row.get("net_pct"))
    if signal is not None and final is not None:
        if abs(signal - final) < 1e-6:
            parts.append("Signal-only Net % matches the final result.")
        else:
            parts.append(
                f"Signal-only Net % (before TSL): {signal:.2f}%. Final includes trailing-stop tune."
            )
    return " ".join(parts)


def format_export_params(row: dict[str, Any], *, is_bh: bool = False) -> str:
    """Every setting a user would need to recreate the strategy manually."""
    if is_bh:
        return "—"
    from trendalgo.backtest.secret_sauce_dossier import is_secret_sauce_indicator
    from trendalgo.device import strings as S

    indicator = str(row.get("indicator") or row.get("strategy_id") or "")
    if is_secret_sauce_indicator(indicator):
        if bool(row.get("ss_lab_pending")):
            return str(S.SECRET_SAUCE_PENDING)
        return str(S.SECRET_SAUCE_PARAMS_STUB)
    parts: list[str] = []
    params = row.get("params")
    if isinstance(params, dict):
        for key, value in params.items():
            if key in {"heartbeat_dossier", "entry_conjuncts", "exit_conjuncts", "conjuncts"}:
                continue
            if isinstance(value, bool):
                parts.append(f"{key}={value}")
            elif isinstance(value, int | float):
                parts.append(f"{key}={int(round(float(value)))}")
            else:
                parts.append(f"{key}={value}")
    tsl = row.get("trailing_stop_loss_pct")
    if tsl is None:
        tsl = row.get("trailing_stop_pct")
    if tsl is not None and tsl not in ("-", ""):
        parts.append(f"tsl={tsl_display_pct(tsl)}%")
    return ", ".join(parts) or "—"


def tsl_display_pct(raw: Any) -> int:
    """Fraction (0.01) or percent (1) → integer percent for display (0 = signal-only)."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0
    if value <= 0.0:
        return 0
    if value < 1.0:
        return max(1, int(round(value * 100.0)))
    return max(0, int(round(value)))


def is_perfect_strategy(row: dict[str, Any]) -> bool:
    """100% win rate and zero TSL hits (non-B&H / non-Oracle)."""
    name = str(row.get("indicator") or "").strip()
    if name in {_BH, "Oracle max"}:
        return False
    hits = _as_int(row.get("tsl_hits"))
    if hits is None or hits != 0:
        return False
    win = _as_float(row.get("win_pct"))
    if win is None:
        return False
    rate = win * 100.0 if 0.0 <= win <= 1.0 else win
    return abs(rate - 100.0) < 1e-6


def filter_perfect_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep Perfect Strategies plus B&H / Oracle max when present."""
    keep = {_BH, "Oracle max"}
    return [
        r for r in rows if is_perfect_strategy(r) or str(r.get("indicator") or "").strip() in keep
    ]


def row_cells(row: dict[str, Any], *, is_bh: bool) -> list[str]:
    tsl = row.get("trailing_stop_loss_pct")
    if tsl is None:
        tsl = row.get("trailing_stop_pct")
    trades = _as_int(row.get("trades"))
    hits = _as_int(row.get("tsl_hits"))
    hit_pct = None
    if trades is not None and hits is not None and trades > 0:
        hit_pct = hits / trades * 100.0
    fees = row.get("fees_paid")
    skip = str(row.get("skip_reason") or "").strip()
    wins, losses = wins_losses(row)
    open_n = open_trades(row)
    if skip and (trades is None or trades == 0):
        open_cell = "—"
        wins_cell = f"0 ({skip})"
        losses_cell = "—"
    elif is_bh or wins is None:
        open_cell = "—"
        wins_cell = "—"
        losses_cell = "—"
    else:
        open_cell = str(open_n if open_n is not None else 0)
        wins_cell = str(wins)
        losses_cell = str(losses if losses is not None else "—")
    strength = None if is_bh else strength_from_row(row)
    if is_bh or tsl in (None, "-", ""):
        tsl_cell = "—"
    elif tsl_display_pct(tsl) == 0:
        tsl_cell = "0% (signal)"
    else:
        tsl_cell = f"{tsl_display_pct(tsl)}%"
    return [
        indicator_label(str(row.get("indicator") or "—"), is_bh=is_bh),
        str(row.get("timeframe") or "—"),
        format_export_params(row, is_bh=is_bh),
        dash(row.get("net_pct"), pct=True),
        _fees_cell(fees),
        open_cell,
        wins_cell,
        losses_cell,
        "—" if is_bh else dash(win_pct(row), pct=True),
        tsl_cell,
        "—" if is_bh or hits is None else str(hits),
        "—" if is_bh else dash(hit_pct, pct=True),
        "—" if strength is None else f"{strength:.1f}",
    ]


def heat_for_rows(rows: list[dict[str, Any]]) -> dict[int, list[str | None]]:
    out: dict[int, list[str | None]] = {}
    for column, (key, invert) in HEAT_COLS.items():
        values = [_metric(row, key) for row in rows]
        out[column] = rank_hex_colors(values, invert=invert)
    return out


def _metric(row: dict[str, Any], key: str) -> float | None:
    is_bh = str(row.get("indicator") or "").strip() == _BH
    if key in {"tsl_hits", "tsl_hit_pct", "strength", "wins", "losses", "open_trades"} and is_bh:
        return None
    if key == "strength":
        return strength_from_row(row)
    if key == "open_trades":
        raw = open_trades(row)
        return float(raw) if raw is not None else None
    if key in {"wins", "losses"}:
        wins, losses = wins_losses(row)
        raw = wins if key == "wins" else losses
        return float(raw) if raw is not None else None
    if key == "tsl_hit_pct":
        trades = _as_int(row.get("trades"))
        hits = _as_int(row.get("tsl_hits"))
        if trades is not None and hits is not None and trades > 0:
            return hits / trades * 100.0
        return None
    if key == "tsl_hits":
        raw = _as_int(row.get("tsl_hits"))
        return float(raw) if raw is not None else None
    if key == "win_pct":
        return win_pct(row)
    return _as_float(row.get(key))


def _fees_cell(value: Any) -> str:
    try:
        if value in (None, "-", ""):
            return "—"
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _as_int(value: Any) -> int | None:
    if value in (None, "-"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value in (None, "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
