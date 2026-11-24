"""Live dashboard canvas + customize apply for Avalonia (AV-G-DSH1/DSH2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "apply_dashboard_customize",
    "apply_dashboard_layout",
    "apply_dashboard_module_mins",
    "load_dashboard_surface",
]


def load_dashboard_surface(root: Path) -> dict[str, Any]:
    from trendalgo.device.portfolio_layout_prefs import load_prefs
    from trendalgo.device.portfolio_module_catalog import CATALOG, catalog_by_category, spec_for
    from trendalgo.results_store.desk_portfolio_payload import (
        load_portfolio_analytics,
        tile_visual_for,
    )

    prefs = load_prefs(root)
    page = next((p for p in prefs.pages if p.id == prefs.active_page_id), None)
    if page is None and prefs.pages:
        page = prefs.pages[0]
    placements = list(page.placements) if page else []
    present = {p.id for p in placements}
    analytics = load_portfolio_analytics(root)
    live = _live_glances(root)
    tiles: list[dict[str, Any]] = []
    for pl in placements:
        meta = spec_for(pl.id)
        title = meta.title if meta else pl.id
        category = meta.category if meta else ""
        visual = tile_visual_for(pl.id, analytics)
        glance = live.get(pl.id) or {}
        if not visual.get("value") and glance.get("value"):
            visual["value"] = str(glance["value"])
        if not visual.get("detail") and glance.get("detail"):
            visual["detail"] = str(glance["detail"])
        tiles.append(
            {
                "id": pl.id,
                "title": title,
                "category": category,
                "col": pl.col,
                "row": pl.row,
                "w": pl.w,
                "h": pl.h,
                **visual,
            }
        )
    catalog = [
        {"id": m.id, "title": m.title, "category": m.category, "w": m.default_w, "h": m.default_h}
        for m in CATALOG
    ]
    customize = [
        {
            "category": cat,
            "modules": [{"id": s.id, "title": s.title, "checked": s.id in present} for s in specs],
        }
        for cat, specs in catalog_by_category()
    ]
    pages = [{"id": p.id, "title": p.name, "placements": len(p.placements)} for p in prefs.pages]
    cols = max(4, int(prefs.grid.cols or 24))
    rows = max(4, int(prefs.grid.rows or 24))
    if placements:
        rows = max(rows, max(p.row + p.h for p in placements))
    return {
        "modules": catalog,
        "tiles": tiles,
        "count": len(catalog),
        "tile_count": len(tiles),
        "demo": bool(analytics.get("demo")),
        "has_data": bool(analytics.get("has_data")),
        "ranges": ["1D", "1W", "1M", "3M", "YTD", "1Y"],
        "range_chips": ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "ALL"],
        "active_range": str(analytics.get("active_range") or "1M"),
        "pages": pages or [{"id": "main", "title": "Main"}],
        "active_page_id": prefs.active_page_id,
        "calendar_cta": True,
        "last_synced_local": str(analytics.get("last_synced_local") or ""),
        "venues_summary": str(analytics.get("venues_summary") or ""),
        "net_worth_usd": float(analytics.get("net_worth_usd") or 0.0),
        "daily_pnl_usd": float(analytics.get("daily_pnl_usd") or 0.0),
        "daily_pnl_pct": float(analytics.get("daily_pnl_pct") or 0.0),
        "health_score": int(analytics.get("health_score") or 0),
        "grid": {
            "cols": cols,
            "rows": rows,
            "gap_px": int(prefs.grid.gap_px or 8),
            "show_grid": bool(prefs.grid.show_grid),
        },
        "customize": customize,
        "module_mins": _module_mins_rows(prefs),
        "live": live,
    }


def apply_dashboard_layout(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Switch active Dashboard page, add a page, set range, or toggle Demo/Live."""
    import json

    from trendalgo.device.portfolio_demo import seed_demo_portfolio
    from trendalgo.device.portfolio_layout_prefs import PageLayout, load_prefs, save_prefs

    prefs = load_prefs(root)
    changed_prefs = False
    if payload.get("add_page"):
        n = len(prefs.pages) + 1
        new_id = f"page-{n}"
        title = str(payload.get("page_title") or f"Page {n}").strip() or f"Page {n}"
        prefs.pages.append(PageLayout(id=new_id, name=title, placements=[]))
        prefs.active_page_id = new_id
        changed_prefs = True
    elif payload.get("active_page_id"):
        want = str(payload["active_page_id"]).strip()
        if any(p.id == want for p in prefs.pages):
            prefs.active_page_id = want
            changed_prefs = True
    if changed_prefs:
        save_prefs(root, prefs)

    layout_path = root / "shell_dashboard_layout.json"
    existing: dict[str, Any] = {}
    if layout_path.is_file():
        try:
            raw = json.loads(layout_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                existing = raw
        except Exception:
            existing = {}

    if "range" in payload and str(payload["range"]).strip():
        existing["range"] = str(payload["range"]).strip().upper()
    if "demo" in payload:
        demo_on = bool(payload["demo"])
        existing["demo"] = demo_on
        if demo_on and not (root / "portfolio-demo.db").is_file():
            seed_demo_portfolio(root / "portfolio-demo.db")
    layout_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "active_page_id": prefs.active_page_id,
        "range": existing.get("range", "1M"),
        "demo": existing.get("demo"),
    }


def apply_dashboard_customize(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Pack selected module ids onto the active page and persist layout prefs."""
    from trendalgo.device.portfolio_grid_pack import pack_placements, required_rows
    from trendalgo.device.portfolio_layout_prefs import load_prefs, save_prefs

    prefs = load_prefs(root)
    page = next((p for p in prefs.pages if p.id == prefs.active_page_id), None)
    if page is None and prefs.pages:
        page = prefs.pages[0]
    if page is None:
        return {"ok": False, "error": "no_page"}
    raw_ids = payload.get("module_ids")
    if not isinstance(raw_ids, list):
        return {"ok": False, "error": "module_ids_required"}
    wanted = [str(x).strip() for x in raw_ids if str(x).strip()]
    try:
        cols = int(payload.get("cols") or prefs.grid.cols or 24)
    except (TypeError, ValueError):
        cols = prefs.grid.cols
    cols = max(4, min(32, cols))
    try:
        rows = int(payload.get("rows") or prefs.grid.rows or 24)
    except (TypeError, ValueError):
        rows = prefs.grid.rows
    show_grid = bool(payload.get("show_grid", prefs.grid.show_grid))
    packed = pack_placements(wanted, existing=list(page.placements), cols=cols)
    page.placements = packed
    prefs.grid.cols = cols
    prefs.grid.rows = max(rows, required_rows(packed, minimum=rows))
    prefs.grid.show_grid = show_grid
    save_prefs(root, prefs)
    return {
        "ok": True,
        "page": page.id,
        "count": len(packed),
        "cols": prefs.grid.cols,
        "rows": prefs.grid.rows,
        "show_grid": prefs.grid.show_grid,
    }


def apply_dashboard_module_mins(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Persist per-module minimum W/H overrides (Settings → Dashboard)."""
    from trendalgo.device.portfolio_layout_prefs import load_prefs, save_prefs
    from trendalgo.device.portfolio_module_catalog import CATALOG, spec_for

    prefs = load_prefs(root)
    if payload.get("reset"):
        prefs.module_mins = {}
        save_prefs(root, prefs)
        return {"ok": True, "reset": True, "count": 0}
    raw = payload.get("mins")
    if not isinstance(raw, list):
        return {"ok": False, "error": "mins_required"}
    overrides: dict[str, tuple[int, int]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        mid = str(item.get("id") or "").strip()
        spec = spec_for(mid)
        if spec is None:
            continue
        try:
            raw_w = item.get("min_w")
            raw_h = item.get("min_h")
            min_w = int(raw_w) if raw_w is not None else int(spec.min_w)
            min_h = int(raw_h) if raw_h is not None else int(spec.min_h)
        except (TypeError, ValueError):
            continue
        min_w = max(1, min(spec.max_w, min_w))
        min_h = max(1, min(spec.max_h, min_h))
        if min_w != spec.min_w or min_h != spec.min_h:
            overrides[mid] = (min_w, min_h)
    prefs.module_mins = overrides
    save_prefs(root, prefs)
    return {"ok": True, "count": len(overrides), "catalog": len(CATALOG)}


def _module_mins_rows(prefs: Any) -> list[dict[str, Any]]:
    from trendalgo.device.portfolio_module_catalog import CATALOG

    out: list[dict[str, Any]] = []
    for spec in CATALOG:
        if spec.id in prefs.module_mins:
            min_w, min_h = prefs.module_mins[spec.id]
        else:
            min_w, min_h = spec.min_w, spec.min_h
        out.append(
            {
                "id": spec.id,
                "title": spec.title,
                "category": spec.category,
                "min_w": min_w,
                "min_h": min_h,
                "default_w": spec.min_w,
                "default_h": spec.min_h,
                "max_w": spec.max_w,
                "max_h": spec.max_h,
            }
        )
    return out


def _live_glances(root: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    try:
        from trendalgo.device.profile import PORTFOLIO_DB
        from trendalgo.portfolio.db import PortfolioStore

        db = root / PORTFOLIO_DB
        if not db.is_file():
            demo = root / "portfolio-demo.db"
            db = demo if demo.is_file() else db
        if not db.is_file():
            return out
        store = PortfolioStore(db)
        account_id = store.get_or_create_account("kraken", "default")
        snap = store.latest_snapshot(account_id)
        if not snap:
            return out
        net = float(snap.get("total_usd") or 0)
        holdings = snap.get("holdings") or []
        n = len(holdings) if isinstance(holdings, list) else 0
        out["total_worth"] = {
            "value": f"${net:,.2f}",
            "detail": f"{n} holdings · live portfolio.db",
        }
        out["pl_insights"] = {
            "value": f"${net:,.2f}",
            "detail": "Latest snapshot total",
        }
        out["assets"] = {
            "value": str(n),
            "detail": "Open holdings",
        }
        out["portfolio_value"] = {
            "value": f"${net:,.2f}",
            "detail": "Snapshot equity",
        }
    except Exception:
        return out
    return out
