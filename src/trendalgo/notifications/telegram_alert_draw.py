"""Matplotlib draw helpers for Telegram alert images (Palette B)."""

from __future__ import annotations

from typing import Any

from trendalgo.device import chart_contrast as C
from trendalgo.notifications.telegram_alert_data import Ohlc


def draw_candles(ax: Any, ohlc: list[Ohlc]) -> None:
    from matplotlib import patches

    width = 0.6
    for i, (o, h, low, c) in enumerate(ohlc):
        up = c >= o
        color = C.CANDLE_UP if up else C.CANDLE_DOWN
        wick = C.CANDLE_UP_WICK if up else C.CANDLE_DOWN_WICK
        ax.vlines(i, low, h, color=wick, linewidth=0.8, zorder=3)
        bottom = min(o, c)
        height = abs(c - o) or (h - low) * 0.02 or 1e-9
        ax.add_patch(
            patches.Rectangle(
                (i - width / 2, bottom),
                width,
                height,
                facecolor=color,
                edgecolor=wick,
                linewidth=0.6,
                zorder=4,
            )
        )
    ax.set_xlim(-1, len(ohlc) + 1)
    lows = [x[2] for x in ohlc]
    highs = [x[1] for x in ohlc]
    pad = (max(highs) - min(lows)) * 0.04 or 1e-6
    ax.set_ylim(min(lows) - pad, max(highs) + pad)


def draw_trades(ax: Any, ohlc: list[Ohlc], trades: list[dict[str, Any]], patches: Any) -> None:
    n = len(ohlc)
    buys: list[int] = []
    sells: list[int] = []
    for tr in trades:
        ei = _idx(tr.get("entry_index", tr.get("entry_i")), n)
        xi = _idx(tr.get("exit_index", tr.get("exit_i")), n)
        try:
            pnl = float(tr.get("pnl_pct") or tr.get("net_pct") or 0.0)
        except (TypeError, ValueError):
            pnl = 0.0
        if ei is not None:
            buys.append(ei)
        if xi is not None:
            sells.append(xi)
            color = C.HOLD_WIN if pnl >= 0 else C.HOLD_LOSS
            if ei is not None and xi > ei:
                try:
                    ep = float(tr.get("entry_price") or ohlc[ei][3])
                    xp = float(tr.get("exit_price") or ohlc[xi][3])
                except (TypeError, ValueError):
                    ep, xp = ohlc[ei][3], ohlc[xi][3]
                ax.add_patch(
                    patches.Rectangle(
                        (ei, min(ep, xp)),
                        xi - ei,
                        abs(xp - ep) or 1e-9,
                        linewidth=0,
                        facecolor=color,
                        alpha=C.HOLD_ALPHA,
                        zorder=2,
                    )
                )
                ax.annotate(
                    f"{pnl:+.1f}%",
                    xy=(xi, ohlc[xi][3]),
                    xytext=(0, 7 if pnl >= 0 else -7),
                    textcoords="offset points",
                    color=color,
                    fontsize=6.5,
                    fontweight="bold",
                    ha="center",
                    zorder=6,
                )
    if buys:
        ax.scatter(
            buys,
            [ohlc[i][3] for i in buys],
            color=C.ENTRY,
            s=55,
            marker="^",
            edgecolors=C.ENTRY_EDGE,
            linewidths=0.4,
            label="Entry",
            zorder=5,
        )
    if sells:
        ax.scatter(
            sells,
            [ohlc[i][3] for i in sells],
            color=C.EXIT,
            s=55,
            marker="v",
            edgecolors=C.EXIT_EDGE,
            linewidths=0.4,
            label="Exit",
            zorder=5,
        )
    if buys or sells:
        ax.legend(
            loc="upper left", facecolor=C.GRID, edgecolor=C.MUTED, labelcolor=C.LABEL, fontsize=8
        )


def draw_table(ax: Any, rows: list[list[str]]) -> None:
    if not rows:
        return
    table = ax.table(cellText=rows[1:], colLabels=rows[0], loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.35)
    for (_r, _c), cell in table.get_celld().items():
        cell.set_facecolor(C.FACE)
        cell.set_edgecolor(C.GRID)
        cell.get_text().set_color(C.LABEL)


def _idx(raw: object, n: int) -> int | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        return None
    try:
        i = int(raw)
    except (TypeError, ValueError):
        return None
    return i if 0 <= i < n else None
