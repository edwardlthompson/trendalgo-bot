"""Candlestick enter composite + leave snapshot PNGs for Telegram (Palette B)."""

from __future__ import annotations

import io
from typing import Any

from trendalgo.device import chart_contrast as C
from trendalgo.notifications.telegram_alert_data import (
    ohlc_from_coin,
    strategy_table_rows,
    trades_from_coin,
)
from trendalgo.notifications.telegram_alert_draw import draw_candles, draw_table, draw_trades
from trendalgo.notifications.telegram_coin_fields import coin_pair, coin_symbol


def build_enter_alert_png(coin: dict[str, Any]) -> bytes | None:
    """Candlesticks + top-strategy trades + top-5/B&H table."""
    ohlc = ohlc_from_coin(coin)
    if len(ohlc) < 2:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")  # type: ignore[attr-defined,unused-ignore]
        import matplotlib.pyplot as plt
        from matplotlib import patches
    except ImportError:
        return None

    fig = plt.figure(figsize=(10.5, 7.2), dpi=120, facecolor=C.FACE)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1.1], hspace=0.28)
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(C.FACE)
    draw_candles(ax, ohlc)
    draw_trades(ax, ohlc, trades_from_coin(coin), patches)
    ax.set_title(f"{coin_pair(coin)} · top strategy", color=C.LABEL, fontsize=11, pad=8)
    ax.tick_params(colors=C.MUTED, labelsize=7)
    ax.grid(True, color=C.GRID, alpha=0.35)
    for spine in ax.spines.values():
        spine.set_color(C.GRID)
    ax_t = fig.add_subplot(gs[1])
    ax_t.set_facecolor(C.FACE)
    ax_t.axis("off")
    ax_t.set_title(f"{coin_pair(coin)} · Backtest Ranked Strategies", color=C.LABEL, fontsize=10)
    draw_table(ax_t, strategy_table_rows(coin))
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=C.FACE)
        return buf.getvalue()
    except Exception:
        return None
    finally:
        plt.close(fig)


def build_exit_alert_png(coin: dict[str, Any]) -> bytes | None:
    """Leave snapshot: candles + entry/exit markers."""
    ohlc = ohlc_from_coin(coin)
    if len(ohlc) < 2:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")  # type: ignore[attr-defined,unused-ignore]
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(9, 3.4), dpi=120, facecolor=C.FACE)
    ax.set_facecolor(C.FACE)
    draw_candles(ax, ohlc)
    closes = [c for _, _, _, c in ohlc]
    ax.scatter([0], [closes[0]], color=C.ENTRY, s=55, marker="^", zorder=5, edgecolors=C.ENTRY_EDGE)
    ax.scatter(
        [len(closes) - 1],
        [closes[-1]],
        color=C.EXIT,
        s=55,
        marker="v",
        zorder=5,
        edgecolors=C.EXIT_EDGE,
    )
    ax.set_title(f"{coin_symbol(coin)} Exit Snapshot", color=C.LABEL, fontsize=11)
    ax.tick_params(colors=C.MUTED, labelsize=7)
    ax.grid(True, color=C.GRID, alpha=0.35)
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=C.FACE)
        return buf.getvalue()
    except Exception:
        return None
    finally:
        plt.close(fig)
