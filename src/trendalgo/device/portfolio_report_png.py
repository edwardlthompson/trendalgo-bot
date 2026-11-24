"""2x high-DPI offscreen Qt QPainter Executive Dashboard Share Card PNG."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from trendalgo.device.export_qt import ensure_export_qapp
from trendalgo.results_store.desk_portfolio_payload import load_portfolio_analytics

__all__ = ["render_dashboard_report_png"]

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


def render_dashboard_report_png(root: Path, dest: Path) -> Path:
    """Render a crisp 2x high-DPI Dashboard Share Card to *dest*."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import (
        QColor,
        QFont,
        QImage,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
    )

    ensure_export_qapp(root, force_dark=True)
    a = load_portfolio_analytics(root)
    w, h = 1600, 1000
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(QColor("#0B1120"))

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0.0, QColor("#0B1120"))
    bg.setColorAt(1.0, QColor("#111827"))
    p.fillRect(0, 0, w, h, bg)

    # Header
    p.setPen(QColor("#F8FAFC"))
    p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    p.drawText(48, 62, "TrendAlgo Portfolio Executive Card")

    mode_str = "DEMO" if a.get("demo") else "LIVE"
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    p.setPen(QColor("#94A3B8"))
    p.setFont(QFont("Segoe UI", 12))
    p.drawText(
        48, 90, f"{mode_str} · {a.get('venues_summary')} · Range {a.get('active_range')} · {stamp}"
    )

    # Hero KPI Cards
    net = float(a.get("net_worth_usd") or 0.0)
    daily_usd = float(a.get("daily_pnl_usd") or 0.0)
    daily_pct = float(a.get("daily_pnl_pct") or 0.0)
    unreal = float(a.get("unrealized_usd") or 0.0)
    health = int(a.get("health_score") or 0)
    dd = float(a.get("max_drawdown_pct") or 0.0)
    kpis = [
        ("TOTAL NET WORTH", _money(net), "#F8FAFC"),
        (
            "PERIOD P&L",
            f"{_signed_money(daily_usd)} ({daily_pct:+.2%})",
            "#3DDC97" if daily_usd >= 0 else "#FF6B6B",
        ),
        ("UNREALIZED P&L", _signed_money(unreal), "#3DDC97" if unreal >= 0 else "#FF6B6B"),
        ("HEALTH / MAX DD", f"{health}/100 · {dd:.2%}", "#5B9DFF"),
    ]
    cw = (w - 96 - 36) / 4.0
    for i, (lbl, val, col) in enumerate(kpis):
        x = 48 + i * (cw + 12)
        rect = QRectF(x, 118, cw, 92)
        p.setBrush(QColor("#131C2E"))
        p.setPen(QPen(QColor("#1E293B"), 1.5))
        p.drawRoundedRect(rect, 12, 12)
        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(QRectF(x + 16, 130, cw - 32, 20), Qt.AlignmentFlag.AlignLeft, lbl)
        p.setPen(QColor(col))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        p.drawText(QRectF(x + 16, 156, cw - 32, 40), Qt.AlignmentFlag.AlignLeft, val)

    # Equity Curve Panel (Left)
    eq_rect = QRectF(48, 234, 980, 360)
    p.setBrush(QColor("#131C2E"))
    p.setPen(QPen(QColor("#1E293B"), 1.5))
    p.drawRoundedRect(eq_rect, 12, 12)
    p.setPen(QColor("#E2E8F0"))
    p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    p.drawText(68, 266, "Portfolio Equity Curve")

    equity: list[dict[str, Any]] = list(a.get("equity") or [])
    if len(equity) >= 2:
        vals = [float(pt.get("total_usd") or 0.0) for pt in equity]
        lo, hi = min(vals), max(vals)
        span = max(hi - lo, 1.0)
        px0, py0, pw, ph = 72.0, 290.0, 932.0, 276.0
        pts = [
            QPointF(px0 + (i / max(1, len(vals) - 1)) * pw, py0 + ph - ((v - lo) / span) * ph)
            for i, v in enumerate(vals)
        ]
        fill_path = QPainterPath()
        fill_path.moveTo(px0, py0 + ph)
        for pt in pts:
            fill_path.lineTo(pt)
        fill_path.lineTo(pts[-1].x(), py0 + ph)
        fill_path.closeSubpath()
        grad = QLinearGradient(0, py0, 0, py0 + ph)
        grad.setColorAt(0.0, QColor(61, 220, 151, 90))
        grad.setColorAt(1.0, QColor(61, 220, 151, 5))
        p.fillPath(fill_path, grad)
        line_path = QPainterPath(pts[0])
        for pt in pts[1:]:
            line_path.lineTo(pt)
        p.setPen(QPen(QColor("#3DDC97"), 3.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line_path)
    else:
        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(
            eq_rect, Qt.AlignmentFlag.AlignCenter, "Equity curve builds across daily snapshots"
        )

    # Allocation Donut Panel (Right)
    al_rect = QRectF(1048, 234, 504, 360)
    p.setBrush(QColor("#131C2E"))
    p.setPen(QPen(QColor("#1E293B"), 1.5))
    p.drawRoundedRect(al_rect, 12, 12)
    p.setPen(QColor("#E2E8F0"))
    p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    p.drawText(1068, 266, "Asset Allocation")

    alloc: list[dict[str, Any]] = list(a.get("allocation") or [])[:6]
    if alloc:
        donut_rect = QRectF(1088, 305, 190, 190)
        start_ang = 90 * 16
        for i, row in enumerate(alloc):
            pct = float(row.get("pct") or 0.0)
            span_ang = -int(round(pct * 360 * 16))
            p.setPen(
                QPen(
                    QColor(_PALETTE[i % len(_PALETTE)]),
                    26,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.FlatCap,
                )
            )
            p.drawArc(donut_rect, start_ang, span_ang)
            start_ang += span_ang
        for i, row in enumerate(alloc):
            ly = 320 + i * 34
            col = _PALETTE[i % len(_PALETTE)]
            p.fillRect(QRectF(1310, ly, 12, 12), QColor(col))
            p.setPen(QColor("#E2E8F0"))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.drawText(
                1330, ly + 11, f"{row.get('asset')}  {float(row.get('pct') or 0) * 100:.1f}%"
            )

    # Top Holdings Table (Bottom)
    tb_rect = QRectF(48, 616, w - 96, 336)
    p.setBrush(QColor("#131C2E"))
    p.setPen(QPen(QColor("#1E293B"), 1.5))
    p.drawRoundedRect(tb_rect, 12, 12)
    p.setPen(QColor("#E2E8F0"))
    p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
    p.drawText(68, 648, "Top Holdings")

    holdings: list[dict[str, Any]] = list(a.get("holdings") or [])[:8]
    if holdings:
        for i, h in enumerate(holdings):
            ry = 674 + i * 32
            p.setPen(QColor("#F8FAFC"))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.drawText(72, ry + 16, str(h.get("asset") or ""))
            p.setPen(QColor("#94A3B8"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(200, ry + 16, f"Qty: {float(h.get('quantity') or 0):.4g}")
            p.drawText(460, ry + 16, f"Price: {_money(float(h.get('price_usd') or 0))}")
            p.setPen(QColor("#F8FAFC"))
            p.drawText(760, ry + 16, f"Value: {_money(float(h.get('value_usd') or 0))}")
            p.drawText(1040, ry + 16, f"Weight: {float(h.get('allocation_pct') or 0):.1f}%")
            pnl = float(h.get("unrealized_pnl_usd") or 0.0)
            p.setPen(QColor("#3DDC97" if pnl >= 0 else "#FF6B6B"))
            p.drawText(1280, ry + 16, f"P&L: {_signed_money(pnl)}")
    else:
        p.setPen(QColor("#94A3B8"))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(
            tb_rect,
            Qt.AlignmentFlag.AlignCenter,
            "Connect exchange keys and click Sync Live to populate holdings",
        )

    p.end()
    out = Path(dest)
    if out.suffix.lower() != ".png":
        out = Path(f"{out}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not img.save(str(out), "PNG"):
        raise OSError(f"failed to save dashboard PNG to {out}")
    return out
