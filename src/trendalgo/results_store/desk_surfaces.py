"""Pure exporters for Avalonia Results / DEX / chart stubs (AV-G4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.dex_watch_model import load_dex_watch_rows
from trendalgo.device.indicator_strength import strength_from_row
from trendalgo.device.lts_scan_model import load_lts_rows
from trendalgo.device.trade_counts import open_trades, win_pct, wins_losses
from trendalgo.results_store.desk_chart_surface import chart_summary_from_coin

__all__ = [
    "chart_summary_from_coin",
    "enrich_strategy_row_metrics",
    "find_coin",
    "load_dex_surface",
    "load_events_surface",
    "sauce_dossier_from_row",
    "strategy_sheet_from_coin",
]

_BH = "B&H"


def _net(row: dict[str, Any]) -> float | None:
    for key in ("net_pct", "net", "return_pct", "gain"):
        raw = row.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def enrich_strategy_row_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """Stamp derived open_trades / wins / losses / win_pct / strength onto a strategy dict."""
    out = dict(row)
    ind = str(out.get("indicator") or "").strip()
    is_bh = ind == _BH
    if is_bh:
        return out
    open_n = open_trades(out)
    wins, losses = wins_losses(out)
    if out.get("open_trades") is None and open_n is not None:
        out["open_trades"] = open_n
    if out.get("wins") is None and wins is not None:
        out["wins"] = wins
    if out.get("losses") is None and losses is not None:
        out["losses"] = losses
    if out.get("win_pct") is None:
        wp = win_pct(out)
        if wp is not None:
            out["win_pct"] = round(wp, 2)
    if out.get("strength") is None:
        s = strength_from_row(out)
        if s is not None:
            out["strength"] = s
    return out


def strategy_sheet_from_coin(coin: dict[str, Any]) -> list[dict[str, Any]]:
    raw = coin.get("backtest_top_strategies")
    strategies = [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    bh = coin.get("backtest_buy_hold")
    oracle = coin.get("backtest_oracle_max")
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in strategies:
        name = str(row.get("indicator") or "").strip()
        if name in {_BH, "Oracle max"}:
            continue
        net = _net(row)
        if net is None:
            continue
        ranked.append((net, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    out = [enrich_strategy_row_metrics(row) for _, row in ranked]
    if isinstance(bh, dict) and not any(str(r.get("indicator") or "").strip() == _BH for r in out):
        row = dict(bh)
        row.setdefault("indicator", _BH)
        out.append(row)
    if isinstance(oracle, dict) and not any(
        str(r.get("indicator") or "").strip() == "Oracle max" for r in out
    ):
        row = dict(oracle)
        row.setdefault("indicator", "Oracle max")
        out.append(enrich_strategy_row_metrics(row))
    out.sort(key=lambda row: (_net(row) is not None, _net(row) or 0.0), reverse=True)
    return out


def find_coin(root: Path, pair: str, *, lane: str = "crypto") -> dict[str, Any] | None:
    needle = str(pair or "").strip().upper()
    for row in load_lts_rows(root, lane=lane):
        if str(row.get("pair") or "").strip().upper() == needle:
            return row
    return None


def load_dex_surface(root: Path) -> list[dict[str, Any]]:
    return load_dex_watch_rows(root)


def load_events_surface(root: Path, coin: dict[str, Any] | str) -> list[dict[str, Any]]:
    from trendalgo.device.calendar.coin_window import load_coin_events

    events = load_coin_events(root, coin)
    out: list[dict[str, Any]] = []
    for ev in events:
        if isinstance(ev, dict):
            out.append(ev)
            continue
        cats = getattr(ev, "categories", ()) or ()
        out.append(
            {
                "title": str(getattr(ev, "title", "")),
                "date": str(getattr(ev, "date", "")),
                "displayed_date": str(
                    getattr(ev, "displayed_date", "") or getattr(ev, "date", "")[:10]
                ),
                "category": ", ".join(str(c) for c in cats),
                "source": str(getattr(ev, "source", "")),
                "url": str(getattr(ev, "url", "") or ""),
                "is_estimated": bool(getattr(ev, "is_estimated", False)),
            }
        )
    return out


def sauce_dossier_from_row(row: dict[str, Any]) -> dict[str, Any]:
    raw_params = row.get("params")
    params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
    dossier = row.get("heartbeat_dossier") or params.get("heartbeat_dossier") or {}
    return dict(dossier) if isinstance(dossier, dict) else {}
