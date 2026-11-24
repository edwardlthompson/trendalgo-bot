"""Executive Portfolio HTML/PDF-ready report & enriched CSV bundle exporter."""

from __future__ import annotations

import csv
import html
import io
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from trendalgo.device.export_model import default_export_dir
from trendalgo.device.export_prefs import remember_export_dir
from trendalgo.results_store.desk_portfolio_payload import load_portfolio_analytics

__all__ = [
    "export_portfolio_csv_bundle",
    "export_portfolio_html_report",
    "run_portfolio_report_export",
]

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


def _money(val: float) -> str:
    return f"${val:,.2f}"


def _signed_money(val: float) -> str:
    sign = "+" if val >= 0 else "-"
    return f"{sign}${abs(val):,.2f}"


def _svg_equity_chart(equity: list[dict[str, Any]], width: int = 640, height: int = 210) -> str:
    if len(equity) < 2:
        return (
            f'<svg viewBox="0 0 {width} {height}" class="chart-svg">'
            f'<text x="50%" y="50%" text-anchor="middle" fill="#94A3B8" font-size="13">'
            f"Equity curve accumulates after 2+ daily snapshots</text></svg>"
        )
    vals = [float(p.get("total_usd") or 0.0) for p in equity]
    dates = [str(p.get("date") or p.get("captured_at") or "")[:10] for p in equity]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 1.0)
    pad_l, pad_r, pad_t, pad_b = 58, 16, 16, 26
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b
    coords: list[tuple[float, float]] = []
    n = len(vals)
    for i, v in enumerate(vals):
        x = pad_l + (i / max(1, n - 1)) * pw
        y = pad_t + ph - ((v - lo) / span) * ph
        coords.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{pad_l:.1f},{pad_t + ph:.1f} {poly} {coords[-1][0]:.1f},{pad_t + ph:.1f}"
    grid_lines = []
    for frac in (0.0, 0.5, 1.0):
        gy = pad_t + ph - frac * ph
        gv = lo + frac * span
        grid_lines.append(
            f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" '
            f'stroke="#1E293B" stroke-dasharray="3,3" />'
            f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" fill="#94A3B8" font-size="10">'
            f"{html.escape(_money(gv))}</text>"
        )
    start_lbl = html.escape(dates[0])
    end_lbl = html.escape(dates[-1])
    return (
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg">'
        f'<defs><linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#3DDC97" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="#3DDC97" stop-opacity="0.02"/>'
        f"</linearGradient></defs>"
        f"{''.join(grid_lines)}"
        f'<polygon points="{area}" fill="url(#eqGrad)" />'
        f'<polyline points="{poly}" fill="none" stroke="#3DDC97" stroke-width="2.4" stroke-linejoin="round" />'
        f'<text x="{pad_l}" y="{height - 6}" fill="#94A3B8" font-size="10">{start_lbl}</text>'
        f'<text x="{width - pad_r}" y="{height - 6}" text-anchor="end" fill="#94A3B8" font-size="10">{end_lbl}</text>'
        f"</svg>"
    )


def _svg_donut_chart(allocation: list[dict[str, Any]], net_worth: float) -> str:
    if not allocation:
        return '<svg viewBox="0 0 360 210" class="chart-svg"><text x="50%" y="50%" text-anchor="middle" fill="#94A3B8" font-size="13">No holdings</text></svg>'
    slices = allocation[:6]
    other_pct = sum(float(a.get("pct") or 0.0) for a in allocation[6:])
    items = [(str(a.get("asset") or ""), float(a.get("pct") or 0.0) * 100.0) for a in slices]
    if other_pct > 0:
        items.append(("Other", other_pct * 100.0))

    cx, cy, r, stroke_w = 95.0, 105.0, 66.0, 26.0
    circ = 2.0 * math.pi * r
    offset = 0.0
    arcs: list[str] = []
    legends: list[str] = []
    for i, (label, pct) in enumerate(items):
        color = _PALETTE[i % len(_PALETTE)]
        dash = max(0.5, (pct / 100.0) * circ)
        arcs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke_w}" stroke-dasharray="{dash:.2f} {circ:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})" />'
        )
        offset += dash
        ly = 30 + i * 24
        legends.append(
            f'<rect x="200" y="{ly - 10}" width="10" height="10" rx="2" fill="{color}" />'
            f'<text x="216" y="{ly - 1}" fill="#E2E8F0" font-size="11.5" font-weight="600">{html.escape(label)}</text>'
            f'<text x="348" y="{ly - 1}" text-anchor="end" fill="#94A3B8" font-size="11">{pct:.1f}%</text>'
        )
    return (
        f'<svg viewBox="0 0 360 210" class="chart-svg">'
        f"{''.join(arcs)}"
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" fill="#94A3B8" font-size="10">NET WORTH</text>'
        f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" fill="#F8FAFC" font-size="12.5" font-weight="700">{html.escape(_money(net_worth))}</text>'
        f"{''.join(legends)}"
        f"</svg>"
    )


def _svg_daily_bars(equity: list[dict[str, Any]], width: int = 640, height: int = 160) -> str:
    if len(equity) < 2:
        return f'<svg viewBox="0 0 {width} {height}" class="chart-svg"><text x="50%" y="50%" text-anchor="middle" fill="#94A3B8" font-size="12">Daily bars appear after 2+ days</text></svg>'
    deltas = [
        (
            str(equity[i].get("date") or equity[i].get("captured_at") or "")[5:10],
            float(equity[i].get("total_usd") or 0.0) - float(equity[i - 1].get("total_usd") or 0.0),
        )
        for i in range(1, len(equity))
    ][-28:]
    max_abs = max((abs(v) for _, v in deltas), default=1.0) or 1.0
    pad_x, mid_y, half_h = 20.0, height / 2.0, (height - 36.0) / 2.0
    slot = (width - 2 * pad_x) / max(1, len(deltas))
    bw = max(4.0, slot * 0.68)
    bars = [
        f'<line x1="{pad_x}" y1="{mid_y}" x2="{width - pad_x}" y2="{mid_y}" stroke="#334155" />'
    ]
    for i, (_lbl, val) in enumerate(deltas):
        bh = max(2.0, (abs(val) / max_abs) * half_h)
        bx = pad_x + i * slot + (slot - bw) / 2.0
        by = mid_y - bh if val >= 0 else mid_y
        col = "#3DDC97" if val >= 0 else "#FF6B6B"
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="{col}" />'
        )
    return f'<svg viewBox="0 0 {width} {height}" class="chart-svg">{"".join(bars)}</svg>'


def export_portfolio_html_report(root: Path, dest: Path | None = None) -> Path:
    """Generate a self-contained, print/PDF-ready Executive Portfolio HTML report."""
    a = load_portfolio_analytics(root)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    day = datetime.now().astimezone().date().isoformat()
    out = dest if dest is not None else (default_export_dir(root) / f"portfolio-report-{day}.html")
    if out.suffix.lower() not in (".html", ".htm"):
        out = Path(f"{out}.html")
    out.parent.mkdir(parents=True, exist_ok=True)

    net = float(a.get("net_worth_usd") or 0.0)
    daily_usd = float(a.get("daily_pnl_usd") or 0.0)
    daily_pct = float(a.get("daily_pnl_pct") or 0.0)
    unreal = float(a.get("unrealized_usd") or 0.0)
    dd = float(a.get("max_drawdown_pct") or 0.0)
    health = int(a.get("health_score") or 0)
    mode_lbl = "DEMO PREVIEW" if a.get("demo") else "LIVE PORTFOLIO"

    holdings_rows_html = []
    for h in a.get("holdings") or []:
        pnl = float(h.get("unrealized_pnl_usd") or 0.0)
        cost = float(h.get("cost_basis_usd") or 0.0)
        pnl_pct = (pnl / cost * 100.0) if cost > 0 else 0.0
        chg = h.get("change_24h_pct")
        chg_s = f"{float(chg):+.2f}%" if isinstance(chg, (int, float)) else "—"
        chg_cls = (
            "pos"
            if isinstance(chg, (int, float)) and chg >= 0
            else ("neg" if isinstance(chg, (int, float)) else "muted")
        )
        pnl_cls = "pos" if pnl >= 0 else "neg"
        alloc_pct = float(h.get("allocation_pct") or 0.0)
        holdings_rows_html.append(
            "<tr>"
            f"<td><strong>{html.escape(str(h.get('asset') or ''))}</strong> <span class='badge'>{html.escape(str(h.get('venues') or ''))}</span></td>"
            f"<td class='num'>{float(h.get('quantity') or 0.0):,.6g}</td>"
            f"<td class='num'>{html.escape(_money(float(h.get('price_usd') or 0.0)))}</td>"
            f"<td class='num {chg_cls}'>{html.escape(chg_s)}</td>"
            f"<td class='num'><strong>{html.escape(_money(float(h.get('value_usd') or 0.0)))}</strong></td>"
            f"<td class='num'>{alloc_pct:.2f}%<div class='bar'><span style='width:{min(100.0, alloc_pct):.1f}%'></span></div></td>"
            f"<td class='num'>{html.escape(_money(cost))}</td>"
            f"<td class='num {pnl_cls}'>{html.escape(_signed_money(pnl))} ({pnl_pct:+.2f}%)</td>"
            "</tr>"
        )

    venue_rows_html = []
    for acc in a.get("accounts") or []:
        v_usd = float(acc.get("total_usd") or 0.0)
        w_pct = (v_usd / net * 100.0) if net > 0 else 0.0
        venue_rows_html.append(
            "<tr>"
            f"<td><strong>{html.escape(str(acc.get('exchange') or '').capitalize())}</strong></td>"
            f"<td>{html.escape(str(acc.get('account_type') or 'spot'))}</td>"
            f"<td class='num'>{int(acc.get('holdings_count') or 0)}</td>"
            f"<td class='num'>{html.escape(_money(v_usd))}</td>"
            f"<td class='num'>{w_pct:.1f}%</td>"
            "</tr>"
        )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>TrendAlgo Executive Portfolio Report · {html.escape(day)}</title>
<style>
  :root {{ --bg:#0B1120; --card:#111827; --border:#1E293B; --text:#F8FAFC; --muted:#94A3B8; --up:#3DDC97; --down:#FF6B6B; --accent:#5B9DFF; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:28px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); }}
  .wrap {{ max-width:1120px; margin:0 auto; }}
  .header {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:1px solid var(--border); padding-bottom:16px; margin-bottom:20px; }}
  .title {{ font-size:24px; font-weight:700; margin:0; }}
  .sub {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .pill {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:700; background:#1E293B; color:var(--up); border:1px solid #334155; }}
  .kpis {{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-bottom:20px; }}
  .kpi {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px 14px; }}
  .kpi .lbl {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; }}
  .kpi .val {{ font-size:18px; font-weight:700; margin-top:4px; }}
  .grid2 {{ display:grid; grid-template-columns:1.65fr 1fr; gap:16px; margin-bottom:16px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:12px; padding:16px; margin-bottom:16px; }}
  .card h2 {{ font-size:14px; margin:0 0 10px; color:#E2E8F0; }}
  .chart-svg {{ width:100%; height:auto; display:block; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th, td {{ padding:9px 8px; border-bottom:1px solid var(--border); text-align:left; }}
  th {{ color:var(--muted); font-weight:600; font-size:11px; text-transform:uppercase; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .pos {{ color:var(--up); }} .neg {{ color:var(--down); }} .muted {{ color:var(--muted); }}
  .badge {{ font-size:10px; padding:2px 6px; border-radius:4px; background:#1E293B; color:var(--muted); margin-left:4px; }}
  .bar {{ height:4px; background:#1E293B; border-radius:2px; margin-top:3px; overflow:hidden; }}
  .bar span {{ display:block; height:100%; background:var(--accent); }}
  .foot {{ color:var(--muted); font-size:11px; margin-top:16px; text-align:center; }}
  @media print {{
    body {{ background:#FFFFFF; color:#0F172A; padding:12px; }}
    .card, .kpi {{ background:#FFFFFF; border-color:#CBD5E1; break-inside:avoid; }}
    th {{ color:#475569; }} td, th {{ border-color:#E2E8F0; }}
    .pill {{ background:#F1F5F9; color:#0F172A; border-color:#CBD5E1; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div>
      <h1 class="title">TrendAlgo Executive Portfolio Report</h1>
      <div class="sub">Generated {html.escape(stamp)} · Venues: {html.escape(str(a.get("venues_summary") or "—"))} · Range: {html.escape(str(a.get("active_range") or "1M"))}</div>
    </div>
    <div><span class="pill">{mode_lbl} · Health {health}/100</span></div>
  </div>
  <div class="kpis">
    <div class="kpi"><div class="lbl">Total Net Worth</div><div class="val">{html.escape(_money(net))}</div></div>
    <div class="kpi"><div class="lbl">Period P&amp;L</div><div class="val {"pos" if daily_usd >= 0 else "neg"}">{html.escape(_signed_money(daily_usd))} ({daily_pct:+.2%})</div></div>
    <div class="kpi"><div class="lbl">Unrealized P&amp;L</div><div class="val {"pos" if unreal >= 0 else "neg"}">{html.escape(_signed_money(unreal))}</div></div>
    <div class="kpi"><div class="lbl">Max Drawdown</div><div class="val">{dd:.2%}</div></div>
    <div class="kpi"><div class="lbl">Cash Drag</div><div class="val">{float(a.get("cash_drag_pct") or 0.0):.1f}%</div></div>
    <div class="kpi"><div class="lbl">Top Asset Share</div><div class="val">{float(a.get("concentration_pct") or 0.0):.1f}%</div></div>
  </div>
  <div class="grid2">
    <div class="card"><h2>Portfolio Equity Curve</h2>{_svg_equity_chart(list(a.get("equity") or []))}</div>
    <div class="card"><h2>Asset Allocation</h2>{_svg_donut_chart(list(a.get("allocation") or []), net)}</div>
  </div>
  <div class="card"><h2>Daily Session P&amp;L</h2>{_svg_daily_bars(list(a.get("equity") or []))}</div>
  <div class="card">
    <h2>Connected Venues ({len(venue_rows_html)})</h2>
    <table><thead><tr><th>Venue</th><th>Type</th><th class="num">Holdings</th><th class="num">Balance (USD)</th><th class="num">Weight</th></tr></thead>
    <tbody>{"".join(venue_rows_html) or '<tr><td colspan="5" class="muted">No synced venues yet.</td></tr>'}</tbody></table>
  </div>
  <div class="card">
    <h2>Asset Holdings &amp; Cost Basis ({len(holdings_rows_html)})</h2>
    <table><thead><tr><th>Asset</th><th class="num">Quantity</th><th class="num">Price</th><th class="num">24h</th><th class="num">Value</th><th class="num">Weight</th><th class="num">Cost Basis</th><th class="num">Unrealized P&amp;L</th></tr></thead>
    <tbody>{"".join(holdings_rows_html) or '<tr><td colspan="8" class="muted">No holdings yet.</td></tr>'}</tbody></table>
  </div>
  <div class="foot">TrendAlgo · Read-only portfolio analytics report. Use browser Print (Ctrl+P) → Save as PDF for archival sharing. Not financial or tax advice.</div>
</div>
</body>
</html>"""
    out.write_text(doc, encoding="utf-8")
    remember_export_dir(root, out)
    return out


def export_portfolio_csv_bundle(
    root: Path, dest_dir: Path | None = None, *, holdings_dest: Path | None = None
) -> dict[str, str]:
    """Write enriched holdings CSV and equity history CSV."""
    a = load_portfolio_analytics(root)
    day = datetime.now().astimezone().date().isoformat()
    out_dir = (
        holdings_dest.parent
        if holdings_dest is not None
        else (dest_dir or default_export_dir(root))
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    holdings_path = (
        holdings_dest if holdings_dest is not None else (out_dir / f"portfolio-holdings-{day}.csv")
    )
    equity_path = out_dir / f"portfolio-equity-{day}.csv"

    h_buf = io.StringIO()
    hw = csv.writer(h_buf)
    hw.writerow(
        [
            "asset",
            "venue",
            "quantity",
            "price_usd",
            "value_usd",
            "allocation_pct",
            "cost_basis_usd",
            "unrealized_pnl_usd",
            "change_24h_pct",
        ]
    )
    for h in a.get("holdings") or []:
        hw.writerow(
            [
                h.get("asset", ""),
                h.get("venues", ""),
                h.get("quantity", 0),
                h.get("price_usd", 0),
                h.get("value_usd", 0),
                h.get("allocation_pct", 0),
                h.get("cost_basis_usd", 0),
                h.get("unrealized_pnl_usd", 0),
                h.get("change_24h_pct", ""),
            ]
        )
    holdings_path.write_text(h_buf.getvalue(), encoding="utf-8")

    e_buf = io.StringIO()
    ew = csv.writer(e_buf)
    ew.writerow(["date", "total_usd", "daily_pnl_usd"])
    eq = list(a.get("equity") or [])
    for i, pt in enumerate(eq):
        tot = float(pt.get("total_usd") or 0.0)
        dpnl = tot - float(eq[i - 1].get("total_usd") or tot) if i > 0 else 0.0
        ew.writerow(
            [str(pt.get("date") or pt.get("captured_at") or "")[:10], round(tot, 2), round(dpnl, 2)]
        )
    equity_path.write_text(e_buf.getvalue(), encoding="utf-8")
    remember_export_dir(root, holdings_path)
    return {"holdings_csv": str(holdings_path), "equity_csv": str(equity_path)}


def run_portfolio_report_export(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """CLI / Shell entrypoint for HTML report or CSV bundle export."""
    kind = str(payload.get("kind") or "html").strip().lower()
    dest_raw = str(payload.get("dest") or "").strip()
    dest = Path(dest_raw) if dest_raw else None
    try:
        if kind in ("csv", "portfolio_csv"):
            paths = export_portfolio_csv_bundle(
                root,
                dest_dir=dest if (dest is not None and dest.is_dir()) else None,
                holdings_dest=dest if (dest is not None and not dest.is_dir()) else None,
            )
            return {
                "ok": True,
                "kind": "csv",
                "path": paths["holdings_csv"],
                "equity_path": paths["equity_csv"],
                "message": f"Exported Holdings + Equity CSV → {Path(paths['holdings_csv']).parent}",
            }
        html_path = export_portfolio_html_report(root, dest=dest)
        return {
            "ok": True,
            "kind": "html",
            "path": str(html_path),
            "message": f"Exported Executive Report → {html_path.name}",
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
