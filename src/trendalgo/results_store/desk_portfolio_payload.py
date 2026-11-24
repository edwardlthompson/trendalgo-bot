"""Rich multi-exchange Portfolio analytics & visual tile builder for Avalonia Dashboard."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.device.coin_icons import coin_icon_path
from trendalgo.device.portfolio_categories import (
    cash_drag_pct,
    category_totals,
    concentration_top_pct,
)
from trendalgo.device.portfolio_compare import local_comparison_curves
from trendalgo.device.portfolio_demo import is_demo_source
from trendalgo.device.time_display import format_display_time
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.drawdown import max_drawdown
from trendalgo.portfolio.health import health_score
from trendalgo.portfolio.metrics import (
    allocation_rows,
    daily_pnl_from_curve,
    enrich_holdings,
    heatmap_rows,
    pl_breakdown,
)
from trendalgo.portfolio.multi_exchange import aggregate_holdings
from trendalgo.portfolio.rebalance import rebalance_suggestions

__all__ = ["load_portfolio_analytics", "tile_visual_for"]

_PALETTE: tuple[str, ...] = (
    "#3DDC97",
    "#5B9DFF",
    "#F59E0B",
    "#A78BFA",
    "#EC4899",
    "#14B8A6",
    "#F97316",
    "#94A3B8",
)


def _read_json_safe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _has_snapshots(db_path: Path) -> bool:
    if not db_path.is_file() or db_path.stat().st_size == 0:
        return False
    try:
        store = PortfolioStore(db_path, create=False)
        for acc in store.list_accounts():
            if store.latest_snapshot(int(acc["id"])) is not None:
                return True
    except (sqlite3.Error, OSError):
        return False
    return False


def _slice_curve_by_range(curve: list[dict[str, Any]], range_key: str) -> list[dict[str, Any]]:
    if not curve:
        return []
    key = (range_key or "1M").strip().upper()
    if key == "ALL":
        return curve
    now_date = datetime.now(UTC).date()
    cutoff_map = {
        "1D": now_date - timedelta(days=1),
        "24H": now_date - timedelta(days=1),
        "1W": now_date - timedelta(days=7),
        "7D": now_date - timedelta(days=7),
        "1M": now_date - timedelta(days=30),
        "3M": now_date - timedelta(days=90),
        "6M": now_date - timedelta(days=180),
        "YTD": now_date.replace(month=1, day=1),
        "1Y": now_date - timedelta(days=365),
    }
    cutoff = cutoff_map.get(key)
    if cutoff is None:
        return curve
    out: list[dict[str, Any]] = []
    for pt in curve:
        raw = str(pt.get("date") or pt.get("captured_at") or "")[:10]
        try:
            d = datetime.fromisoformat(raw).date()
        except ValueError:
            out.append(pt)
            continue
        if d >= cutoff:
            out.append(pt)
    return out if len(out) >= 2 else curve


def _aggregate_equity(store: PortfolioStore) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, float]] = {}
    for acc in store.list_accounts():
        aid = int(acc["id"])
        for row in store.list_daily_aggregates(aid, limit=365):
            d = str(row["date"])
            bucket = by_date.setdefault(
                d,
                {
                    "total_usd": 0.0,
                    "daily_pnl_usd": 0.0,
                    "realized_usd": 0.0,
                    "unrealized_usd": 0.0,
                },
            )
            bucket["total_usd"] += float(row.get("total_usd") or 0.0)
            bucket["daily_pnl_usd"] += float(row.get("daily_pnl_usd") or 0.0)
            bucket["realized_usd"] += float(row.get("realized_pnl_usd") or 0.0)
            bucket["unrealized_usd"] += float(row.get("unrealized_pnl_usd") or 0.0)
    if not by_date:
        return []
    return [
        {"captured_at": d, "date": d, **vals}
        for d, vals in sorted(by_date.items(), key=lambda kv: kv[0])
    ]


def _empty_analytics(root: Path, demo_flag: bool, range_key: str) -> dict[str, Any]:
    return {
        "has_data": False,
        "demo": demo_flag,
        "active_range": range_key,
        "net_worth_usd": 0.0,
        "daily_pnl_usd": 0.0,
        "daily_pnl_pct": 0.0,
        "realized_usd": 0.0,
        "unrealized_usd": 0.0,
        "total_pl_usd": 0.0,
        "total_cost_usd": 0.0,
        "health_score": 0,
        "max_drawdown_pct": 0.0,
        "cash_drag_pct": 0.0,
        "concentration_pct": 0.0,
        "captured_at": "",
        "last_synced_local": "Not synced yet",
        "venues_summary": "No exchange synced",
        "accounts": [],
        "holdings": [],
        "allocation": [],
        "categories": [],
        "equity": [],
        "compare_top10": [],
        "compare_buy_hold": [],
        "heatmap": [],
        "rebalance": [],
        "open_orders": [],
        "recent_trades": [],
        "fees_paid_usd": 0.0,
    }


def load_portfolio_analytics(root: Path, *, range_override: str | None = None) -> dict[str, Any]:
    """Load complete multi-exchange analytics from portfolio.db or portfolio-demo.db."""
    layout = _read_json_safe(root / "shell_dashboard_layout.json")
    range_key = str(range_override or layout.get("range") or "1M").strip().upper()
    live_db = root / "portfolio.db"
    demo_db = root / "portfolio-demo.db"
    has_live = _has_snapshots(live_db)
    has_demo_file = demo_db.is_file()
    forced_demo = layout.get("demo")
    if forced_demo is True and has_demo_file:
        use_demo = True
        active_db = demo_db
    elif has_live:
        use_demo = False
        active_db = live_db
    elif has_demo_file:
        use_demo = True
        active_db = demo_db
    else:
        return _empty_analytics(root, False, range_key)

    if not _has_snapshots(active_db):
        return _empty_analytics(root, use_demo, range_key)

    store = PortfolioStore(active_db, create=False)
    agg = aggregate_holdings(store)
    accounts = list(agg.get("accounts") or [])
    raw_holdings = list(agg.get("holdings") or [])
    net_worth = float(agg.get("total_usd") or 0.0)

    extras = _read_json_safe(root / "portfolio_live_extras.json") if not use_demo else {}
    raw_chg_map = extras.get("asset_changes_24h")
    changes_24h: dict[str, Any] = raw_chg_map if isinstance(raw_chg_map, dict) else {}

    # Track per-asset primary venue for table display.
    asset_venues: dict[str, list[str]] = {}
    latest_captured = ""
    for acc in accounts:
        snap = store.latest_snapshot(int(acc["account_id"]))
        if not snap:
            continue
        if is_demo_source(str(snap.get("source") or "")):
            use_demo = True
        cap = str(snap.get("captured_at") or "")
        if cap > latest_captured:
            latest_captured = cap
        ex_name = str(acc.get("exchange") or "")
        for h in snap.get("holdings") or []:
            sym = str(h.get("asset") or "").upper()
            if sym and ex_name and ex_name not in asset_venues.setdefault(sym, []):
                asset_venues[sym].append(ex_name)

    holdings = enrich_holdings(raw_holdings)
    allocation = allocation_rows(holdings, net_worth)
    alloc_map = {str(a["asset"]): float(a["pct"]) * 100.0 for a in allocation}
    for row in holdings:
        sym = str(row.get("asset") or "")
        row["allocation_pct"] = round(alloc_map.get(sym, 0.0), 2)
        row["venues"] = ", ".join(asset_venues.get(sym, [])) or ("demo" if use_demo else "spot")
        if sym in changes_24h:
            try:
                row["change_24h_pct"] = float(changes_24h[sym])
            except (TypeError, ValueError):
                pass
        icon = coin_icon_path(sym)
        row["icon_path"] = str(icon) if icon is not None else ""

    equity_all = _aggregate_equity(store)
    if len(equity_all) < 2 and not use_demo:
        backfill = extras.get("backfill_curve")
        if isinstance(backfill, list) and len(backfill) >= 2:
            equity_all = [
                {
                    "captured_at": str(p.get("date") or ""),
                    "date": str(p.get("date") or ""),
                    "total_usd": float(p.get("total_usd") or 0.0),
                }
                for p in backfill
                if isinstance(p, dict)
            ]
    if not equity_all and net_worth > 0:
        equity_all = [
            {
                "captured_at": latest_captured or datetime.now(UTC).isoformat(),
                "total_usd": net_worth,
            }
        ]

    equity_sliced = _slice_curve_by_range(equity_all, range_key)
    daily_usd, daily_pct = daily_pnl_from_curve(equity_sliced)
    top10, buy_hold = local_comparison_curves(equity_sliced)
    pl = pl_breakdown(holdings)
    dd = max_drawdown(equity_sliced)
    health = health_score(allocation, dd, daily_pct)
    cats = category_totals(holdings)
    hmap = heatmap_rows(holdings)

    targets: list[dict[str, Any]] = []
    if accounts:
        try:
            targets = list(store.list_allocation_targets(int(accounts[0]["account_id"])))
        except Exception:
            targets = []
    rebal = list(rebalance_suggestions(allocation, targets, net_worth)) if targets else []

    last_synced_local = ""
    if latest_captured:
        last_synced_local = format_display_time(latest_captured) or latest_captured

    venue_names = [str(a.get("exchange") or "") for a in accounts if a.get("exchange")]
    venues_summary = (
        "Demo Top-20"
        if use_demo
        else (", ".join(v.capitalize() for v in venue_names) if venue_names else "Live")
    )

    return {
        "has_data": True,
        "demo": use_demo,
        "active_range": range_key,
        "net_worth_usd": round(net_worth, 2),
        "daily_pnl_usd": daily_usd,
        "daily_pnl_pct": daily_pct,
        "realized_usd": pl.realized_usd,
        "unrealized_usd": pl.unrealized_usd,
        "total_pl_usd": pl.total_usd,
        "total_cost_usd": round(max(0.0, net_worth - pl.unrealized_usd), 2),
        "health_score": int(health),
        "max_drawdown_pct": round(float(dd), 4),
        "cash_drag_pct": round(cash_drag_pct(holdings), 2),
        "concentration_pct": round(concentration_top_pct(holdings, 1), 2),
        "captured_at": latest_captured,
        "last_synced_local": last_synced_local or "Just now",
        "venues_summary": venues_summary,
        "accounts": accounts,
        "holdings": holdings,
        "allocation": allocation,
        "categories": cats,
        "equity": equity_sliced,
        "compare_top10": top10,
        "compare_buy_hold": buy_hold,
        "heatmap": hmap,
        "rebalance": rebal,
        "open_orders": list(extras.get("open_orders") or []),
        "recent_trades": list(extras.get("recent_trades") or []),
        "fees_paid_usd": float(extras.get("fees_paid_usd") or 0.0),
    }


def _money(val: float) -> str:
    return f"${val:,.2f}"


def _signed_money(val: float) -> str:
    sign = "+" if val >= 0 else "-"
    return f"{sign}${abs(val):,.2f}"


def tile_visual_for(module_id: str, a: dict[str, Any]) -> dict[str, Any]:
    """Build rich display + chart payload for any of the 38 catalog modules."""
    has_data = bool(a.get("has_data"))
    net = float(a.get("net_worth_usd") or 0.0)
    daily_usd = float(a.get("daily_pnl_usd") or 0.0)
    daily_pct = float(a.get("daily_pnl_pct") or 0.0)
    unreal = float(a.get("unrealized_usd") or 0.0)
    realized = float(a.get("realized_usd") or 0.0)
    cost = float(a.get("total_cost_usd") or 0.0)
    health = int(a.get("health_score") or 0)
    dd = float(a.get("max_drawdown_pct") or 0.0)
    holdings: list[dict[str, Any]] = list(a.get("holdings") or [])
    alloc: list[dict[str, Any]] = list(a.get("allocation") or [])
    equity: list[dict[str, Any]] = list(a.get("equity") or [])
    cats: list[dict[str, Any]] = list(a.get("categories") or [])
    accounts: list[dict[str, Any]] = list(a.get("accounts") or [])
    open_orders: list[dict[str, Any]] = list(a.get("open_orders") or [])
    recent_trades: list[dict[str, Any]] = list(a.get("recent_trades") or [])
    fees_usd = float(a.get("fees_paid_usd") or 0.0)

    eq_pts: list[tuple[str, float]] = [
        (str(p.get("date") or p.get("captured_at") or "")[:10], float(p.get("total_usd") or 0.0))
        for p in equity
    ]
    eq_series_pts: list[dict[str, Any]] = [{"x": d, "y": y} for d, y in eq_pts]

    if module_id == "total_worth":
        return {
            "visual_kind": "hero_worth",
            "value": _money(net) if has_data else "—",
            "detail": f"{len(holdings)} assets · {a.get('venues_summary')}",
            "delta_text": f"{_signed_money(daily_usd)} ({daily_pct:+.2%})"
            if has_data
            else "Connect exchange keys",
            "delta_sign": 1 if daily_usd > 0 else (-1 if daily_usd < 0 else 0),
            "series": [{"name": "Net Worth", "color": "#3DDC97", "points": eq_series_pts}],
        }

    if module_id == "pl_insights":
        return {
            "visual_kind": "kpi_grid",
            "value": _signed_money(unreal) if has_data else "—",
            "detail": f"Cost {_money(cost)} · Total P&L {_signed_money(unreal)}"
            if has_data
            else "No snapshot yet",
            "delta_text": f"{(unreal / cost):+.2%}" if cost > 0 else "0.00%",
            "delta_sign": 1 if unreal > 0 else (-1 if unreal < 0 else 0),
            "kpis": [
                {"label": "Total Cost", "value": _money(cost) if has_data else "—", "sign": 0},
                {
                    "label": "Unrealized P&L",
                    "value": _signed_money(unreal) if has_data else "—",
                    "sign": 1 if unreal >= 0 else -1,
                },
                {
                    "label": "Realized P&L",
                    "value": _signed_money(realized) if realized != 0 else "Journal pending",
                    "sign": 1 if realized > 0 else 0,
                },
                {
                    "label": "Health Score",
                    "value": f"{health}/100" if has_data else "—",
                    "sign": 1 if health >= 70 else 0,
                },
            ],
        }

    if module_id == "assets":
        hrows = []
        for h in holdings:
            qty = float(h.get("quantity") or 0.0)
            c = float(h.get("cost_basis_usd") or 0.0)
            v = float(h.get("value_usd") or 0.0)
            pnl = float(h.get("unrealized_pnl_usd") or (v - c))
            pnl_pct = (pnl / c * 100.0) if c > 0 else 0.0
            hrows.append(
                {
                    "asset": str(h.get("asset") or ""),
                    "venue": str(h.get("venues") or ""),
                    "icon_path": str(h.get("icon_path") or ""),
                    "quantity": round(qty, 8),
                    "price_usd": round(float(h.get("price_usd") or 0.0), 6),
                    "change_24h_pct": h.get("change_24h_pct"),
                    "value_usd": round(v, 2),
                    "allocation_pct": float(h.get("allocation_pct") or 0.0),
                    "avg_buy_usd": round(c / qty, 6) if qty > 0 else 0.0,
                    "pnl_usd": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                }
            )
        return {
            "visual_kind": "holdings_table",
            "value": f"{len(holdings)} assets",
            "detail": f"Total {_money(net)}" if has_data else "No holdings",
            "holdings_rows": hrows,
        }

    if module_id == "portfolio_value":
        vals = [y for _, y in eq_pts]
        return {
            "visual_kind": "area_chart",
            "value": _money(net) if has_data else "—",
            "detail": f"High {_money(max(vals))} · Low {_money(min(vals))}"
            if vals
            else "No equity history",
            "series": [{"name": "Portfolio Value", "color": "#5B9DFF", "points": eq_series_pts}],
        }

    if module_id == "cumulative_pnl":
        base = eq_pts[0][1] if eq_pts else 0.0
        cum_pts: list[dict[str, Any]] = [{"x": d, "y": round(y - base, 2)} for d, y in eq_pts]
        last_cum = float(cum_pts[-1]["y"]) if cum_pts else 0.0
        return {
            "visual_kind": "area_chart",
            "value": _signed_money(last_cum) if cum_pts else "—",
            "detail": f"Cumulative return over {a.get('active_range')}",
            "delta_sign": 1 if last_cum >= 0 else -1,
            "series": [
                {
                    "name": "Cumulative P&L",
                    "color": "#3DDC97" if last_cum >= 0 else "#FF6B6B",
                    "points": cum_pts,
                }
            ],
        }

    if module_id == "pl_daily":
        bars: list[dict[str, Any]] = []
        for idx in range(1, len(eq_pts)):
            bars.append(
                {
                    "label": eq_pts[idx][0][5:],
                    "value": round(eq_pts[idx][1] - eq_pts[idx - 1][1], 2),
                }
            )
        return {
            "visual_kind": "bar_chart",
            "value": _signed_money(daily_usd) if has_data else "—",
            "detail": f"{len(bars)} session bars",
            "bars": bars[-30:],
        }

    if module_id == "portfolio_vs_market":
        base = eq_pts[0][1] if eq_pts and eq_pts[0][1] else 1.0
        port_pct: list[dict[str, Any]] = [
            {"x": d, "y": round((y / base - 1.0) * 100.0, 2)} for d, y in eq_pts
        ]
        top10_raw = list(a.get("compare_top10") or [])
        bh_raw = list(a.get("compare_buy_hold") or [])
        series: list[dict[str, Any]] = [
            {"name": "Portfolio %", "color": "#3DDC97", "points": port_pct}
        ]
        if top10_raw:
            b1 = float(top10_raw[0].get("total_usd") or 1.0) or 1.0
            series.append(
                {
                    "name": "Top-10 Index %",
                    "color": "#5B9DFF",
                    "points": [
                        {
                            "x": str(p.get("captured_at") or "")[:10],
                            "y": round((float(p.get("total_usd") or b1) / b1 - 1.0) * 100.0, 2),
                        }
                        for p in top10_raw
                    ],
                }
            )
        if bh_raw:
            b2 = float(bh_raw[0].get("total_usd") or 1.0) or 1.0
            series.append(
                {
                    "name": "BTC Buy & Hold %",
                    "color": "#F59E0B",
                    "points": [
                        {
                            "x": str(p.get("captured_at") or "")[:10],
                            "y": round((float(p.get("total_usd") or b2) / b2 - 1.0) * 100.0, 2),
                        }
                        for p in bh_raw
                    ],
                }
            )
        last_pct = float(port_pct[-1]["y"]) if port_pct else 0.0
        return {
            "visual_kind": "multi_line",
            "value": f"{last_pct:+.2f}%" if port_pct else "—",
            "detail": "Portfolio vs BTC & Top-10 benchmark",
            "series": series,
        }

    if module_id == "coin_allocation":
        slices = [
            {
                "label": str(row.get("asset") or ""),
                "value_usd": round(float(row.get("value_usd") or 0.0), 2),
                "pct": round(float(row.get("pct") or 0.0) * 100.0, 2),
                "color": _PALETTE[i % len(_PALETTE)],
            }
            for i, row in enumerate(alloc[:7])
        ]
        if len(alloc) > 7:
            other_val = sum(float(r.get("value_usd") or 0.0) for r in alloc[7:])
            other_pct = sum(float(r.get("pct") or 0.0) * 100.0 for r in alloc[7:])
            slices.append(
                {
                    "label": "Other",
                    "value_usd": round(other_val, 2),
                    "pct": round(other_pct, 2),
                    "color": "#64748B",
                }
            )
        return {
            "visual_kind": "donut",
            "value": f"{len(alloc)} coins",
            "detail": f"Top: {alloc[0]['asset']} ({float(alloc[0]['pct']) * 100:.1f}%)"
            if alloc
            else "No holdings",
            "slices": slices,
        }

    if module_id in ("allocation_by_category", "asset_allocation"):
        slices = [
            {
                "label": str(c.get("category") or ""),
                "value_usd": round(float(c.get("value_usd") or 0.0), 2),
                "pct": round(float(c.get("pct") or 0.0) * 100.0, 2),
                "color": _PALETTE[i % len(_PALETTE)],
            }
            for i, c in enumerate(cats)
            if c.get("value_usd") and float(c["value_usd"]) > 0
        ]
        return {
            "visual_kind": "donut" if module_id == "allocation_by_category" else "alloc_bar",
            "value": _money(net) if has_data else "—",
            "detail": " · ".join(f"{s['label']} {s['pct']:.1f}%" for s in slices)
            or "No allocation",
            "slices": slices,
        }

    if module_id == "heatmap":
        cells = []
        for h in holdings[:16]:
            chg = h.get("change_24h_pct")
            pct_chg = (
                float(chg)
                if isinstance(chg, (int, float))
                else float(h.get("pct_change") or 0.0) * 100.0
            )
            cells.append(
                {
                    "label": str(h.get("asset") or ""),
                    "value_usd": round(float(h.get("value_usd") or 0.0), 2),
                    "pct": float(h.get("allocation_pct") or 0.0),
                    "change_pct": round(pct_chg, 2),
                }
            )
        return {
            "visual_kind": "treemap",
            "value": f"{len(cells)} tiles",
            "detail": "Sized by USD weight · colored by return",
            "cells": cells,
        }

    if module_id in ("top_gainers", "top_losers"):
        reverse = module_id == "top_gainers"
        ranked = sorted(
            holdings,
            key=lambda h: (
                float(h["change_24h_pct"])
                if isinstance(h.get("change_24h_pct"), (int, float))
                else float(h.get("pct_change") or 0.0) * 100.0
            ),
            reverse=reverse,
        )[:5]
        rrows = []
        for h in ranked:
            chg = h.get("change_24h_pct")
            pct_v = (
                float(chg)
                if isinstance(chg, (int, float))
                else float(h.get("pct_change") or 0.0) * 100.0
            )
            rrows.append(
                {
                    "label": str(h.get("asset") or ""),
                    "value": _money(float(h.get("value_usd") or 0.0)),
                    "delta": f"{pct_v:+.2f}%",
                    "sign": 1 if pct_v >= 0 else -1,
                }
            )
        return {
            "visual_kind": "ranked_list",
            "value": rrows[0]["label"] if rrows else "—",
            "detail": rrows[0]["delta"] if rrows else "No movers",
            "ranked_rows": rrows,
        }

    if module_id in ("drawdown", "risk_metrics", "concentration", "cash_drag"):
        if module_id == "drawdown":
            gval = max(0.0, min(100.0, 100.0 - abs(dd) * 100.0))
            return {
                "visual_kind": "gauge",
                "value": f"{dd:.2%}",
                "detail": "Max peak-to-trough drawdown",
                "gauge_value": round(gval, 1),
                "gauge_label": f"DD {dd:.2%}",
            }
        if module_id == "concentration":
            conc = float(a.get("concentration_pct") or 0.0)
            return {
                "visual_kind": "gauge",
                "value": f"{conc:.1f}%",
                "detail": "Largest single-asset share",
                "gauge_value": round(min(100.0, conc), 1),
                "gauge_label": f"Top {conc:.1f}%",
            }
        if module_id == "cash_drag":
            cd = float(a.get("cash_drag_pct") or 0.0)
            return {
                "visual_kind": "gauge",
                "value": f"{cd:.1f}%",
                "detail": "USD & stablecoin reserve share",
                "gauge_value": round(min(100.0, cd), 1),
                "gauge_label": f"Cash {cd:.1f}%",
            }
        return {
            "visual_kind": "kpi_grid",
            "value": f"Health {health}/100" if has_data else "—",
            "detail": f"Daily {daily_pct:+.2%} · DD {dd:.2%}",
            "kpis": [
                {"label": "Health", "value": f"{health}/100", "sign": 1 if health >= 70 else 0},
                {"label": "Max DD", "value": f"{dd:.2%}", "sign": -1 if dd < -0.1 else 0},
                {
                    "label": "Top Weight",
                    "value": f"{float(a.get('concentration_pct') or 0):.1f}%",
                    "sign": 0,
                },
                {
                    "label": "Cash Drag",
                    "value": f"{float(a.get('cash_drag_pct') or 0):.1f}%",
                    "sign": 0,
                },
            ],
        }

    if module_id in ("accounts_strip", "exposure_by_venue"):
        venue_slices: list[dict[str, Any]] = [
            {
                "label": str(acc.get("exchange") or "").capitalize(),
                "value_usd": round(float(acc.get("total_usd") or 0.0), 2),
                "pct": round(
                    (float(acc.get("total_usd") or 0.0) / net * 100.0) if net > 0 else 0.0, 2
                ),
                "color": _PALETTE[i % len(_PALETTE)],
            }
            for i, acc in enumerate(accounts)
        ]
        return {
            "visual_kind": "alloc_bar" if module_id == "accounts_strip" else "donut",
            "value": f"{len(accounts)} venue(s)",
            "detail": " · ".join(
                f"{s['label']} {_money(float(s['value_usd']))}" for s in venue_slices
            )
            or "No venues",
            "slices": venue_slices,
        }

    if module_id == "open_orders":
        return {
            "visual_kind": "orders_table",
            "value": f"{len(open_orders)} open",
            "detail": f"Across {len(accounts)} connected venue(s)",
            "order_rows": [
                {
                    "venue": str(o.get("venue") or ""),
                    "pair": str(o.get("pair") or ""),
                    "side": str(o.get("side") or "").upper(),
                    "price": _money(float(o.get("price") or 0.0)),
                    "amount": f"{float(o.get('amount') or 0.0):g}",
                }
                for o in open_orders[:8]
            ],
        }

    if module_id == "open_positions":
        return {
            "visual_kind": "ranked_list",
            "value": f"{len(holdings)} active",
            "detail": f"Total {_money(net)}",
            "ranked_rows": [
                {
                    "label": f"{h['asset']} ({h.get('venues', '')})",
                    "value": _money(float(h.get("value_usd") or 0.0)),
                    "delta": f"{float(h.get('allocation_pct') or 0.0):.1f}%",
                    "sign": 1 if float(h.get("unrealized_pnl_usd") or 0.0) >= 0 else -1,
                }
                for h in holdings[:8]
            ],
        }

    if module_id in (
        "trading_fees_paid",
        "trading_fees_monthly",
        "funding_fees",
        "recent_activity",
        "trade_stats",
    ):
        if module_id in ("trading_fees_paid", "funding_fees"):
            return {
                "visual_kind": "kpi_grid",
                "value": _money(fees_usd),
                "detail": f"{len(recent_trades)} recent fill(s) inspected",
                "kpis": [
                    {"label": "Fees Paid", "value": _money(fees_usd), "sign": 0},
                    {"label": "Recent Fills", "value": str(len(recent_trades)), "sign": 0},
                ],
            }
        return {
            "visual_kind": "ranked_list",
            "value": f"{len(recent_trades)} trades",
            "detail": f"Fees {_money(fees_usd)}",
            "ranked_rows": [
                {
                    "label": f"{t.get('venue', '').capitalize()} {t.get('pair', '')}",
                    "value": _money(float(t.get("cost_usd") or 0.0)),
                    "delta": str(t.get("side") or "").upper(),
                    "sign": 1 if str(t.get("side") or "").lower() == "buy" else -1,
                }
                for t in recent_trades[:8]
            ],
        }

    if module_id == "best_worst_days" and len(eq_pts) >= 2:
        deltas = [(eq_pts[i][0], eq_pts[i][1] - eq_pts[i - 1][1]) for i in range(1, len(eq_pts))]
        best = max(deltas, key=lambda t: t[1])
        worst = min(deltas, key=lambda t: t[1])
        return {
            "visual_kind": "kpi_grid",
            "value": _signed_money(best[1]),
            "detail": f"Best {best[0]} · Worst {worst[0]}",
            "kpis": [
                {"label": f"Best ({best[0]})", "value": _signed_money(best[1]), "sign": 1},
                {"label": f"Worst ({worst[0]})", "value": _signed_money(worst[1]), "sign": -1},
            ],
        }

    if module_id == "timeline":
        return {
            "visual_kind": "area_chart",
            "value": f"{len(eq_pts)} pts",
            "detail": f"Last sync {a.get('last_synced_local')}",
            "series": [{"name": "Snapshots", "color": "#A78BFA", "points": eq_series_pts}],
        }

    return {
        "visual_kind": "kpi_grid",
        "value": _money(net) if has_data else "—",
        "detail": f"{a.get('venues_summary')} · {len(holdings)} assets",
        "kpis": [
            {"label": "Net Worth", "value": _money(net) if has_data else "—", "sign": 0},
            {
                "label": "Daily P&L",
                "value": _signed_money(daily_usd) if has_data else "—",
                "sign": 1 if daily_usd >= 0 else -1,
            },
        ],
    }
