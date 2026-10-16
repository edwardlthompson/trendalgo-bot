"""Render a simple OHLCV close chart PNG for Telegram sendPhoto (no Qt)."""

from __future__ import annotations

import io
from collections.abc import Sequence
from typing import Any


def chart_png_bytes(
    closes: Sequence[float],
    *,
    title: str = "",
    hold_regions: Sequence[tuple[int, int]] | None = None,
) -> bytes | None:
    """Return PNG bytes, or None when matplotlib is missing / series empty."""
    if len(closes) < 2:
        return None
    try:
        import matplotlib  # type: ignore[import-not-found]

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=120)
    try:
        xs = list(range(len(closes)))
        ax.plot(xs, list(closes), color="#2563eb", linewidth=1.2)
        for start, end in hold_regions or ():
            if 0 <= start < end <= len(closes):
                ax.axvspan(start, end, color="#16a34a", alpha=0.18)
        if title:
            ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.25)
        ax.tick_params(labelsize=8)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        return buf.getvalue()
    except Exception:
        return None
    finally:
        plt.close(fig)


def closes_from_coin(coin: dict[str, Any], *, window: str = "7d") -> list[float]:
    key = "closes_7d" if window == "7d" else "closes_30d"
    raw = coin.get(key) or coin.get("closes") or []
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for item in raw:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            continue
    return out
