"""Format MarketContext dicts for the dedicated pane (no Qt)."""

from __future__ import annotations

from typing import Any

from trendalgo.device import strings as S


def signal_line(ctx: dict[str, Any]) -> str:
    cons = ctx.get("consensus") if isinstance(ctx.get("consensus"), dict) else {}
    signal = str(cons.get("signal") or "Neutral")
    conf = cons.get("confidence")
    conf_s = S.MARKET_CTX_CONFIDENCE.format(pct=int(float(conf or 0)))
    regime = str(ctx.get("regime_label") or "—")
    return f"{signal} · {conf_s} · {S.MARKET_CTX_REGIME}: {regime}"


def levels_lines(ctx: dict[str, Any]) -> list[str]:
    pivots = ctx.get("pivots") if isinstance(ctx.get("pivots"), dict) else {}
    levels = pivots.get("levels") if isinstance(pivots.get("levels"), list) else []
    lines: list[str] = []
    last = ctx.get("last_price")
    for level in levels:
        if not isinstance(level, dict):
            continue
        name = str(level.get("name") or "")
        price = level.get("price")
        strength = level.get("strength")
        marker = ""
        try:
            if (
                last is not None
                and price is not None
                and abs(float(last) - float(price)) / float(last) < 0.002
            ):
                marker = " ←"
        except (TypeError, ValueError, ZeroDivisionError):
            marker = ""
        lines.append(f"{name} {_fmt(price)}  str {int(float(strength or 0))}{marker}")
    struct = ctx.get("structure") if isinstance(ctx.get("structure"), dict) else {}
    if struct.get("nearest_sr_name"):
        lines.append(
            S.MARKET_CTX_NEAREST.format(
                name=struct.get("nearest_sr_name"),
                pct=struct.get("nearest_sr_pct"),
                atr=struct.get("nearest_sr_atr")
                if struct.get("nearest_sr_atr") is not None
                else "—",
            )
        )
    conf_n = int(struct.get("confluence") or 0)
    if conf_n:
        lines.append(S.MARKET_CTX_CONFLUENCE.format(n=conf_n))
    return lines


def risk_line(ctx: dict[str, Any]) -> str:
    risk = ctx.get("risk") if isinstance(ctx.get("risk"), dict) else {}
    r1 = risk.get("rr_to_r1")
    r2 = risk.get("rr_to_r2")
    stop = S.MARKET_CTX_STOP.format(
        pct=risk.get("stop_distance_pct") or 0,
        atr=float(risk.get("stop_distance_atr") or 0),
    )
    rr = S.MARKET_CTX_RR.format(
        r1=r1 if r1 is not None else "—",
        r2=r2 if r2 is not None else "—",
    )
    # Two lines so the Risk module caption is not cropped.
    return f"{stop}\n{rr}"


def structure_lines(ctx: dict[str, Any]) -> list[str]:
    struct = ctx.get("structure") if isinstance(ctx.get("structure"), dict) else {}
    lines: list[str] = []
    if not struct.get("volume_ok"):
        lines.append(S.MARKET_CTX_NO_VOLUME)
    elif struct.get("vwap") is not None:
        lines.append(
            S.MARKET_CTX_VWAP.format(
                price=_fmt(struct.get("vwap")),
                dist=struct.get("vwap_dist_pct")
                if struct.get("vwap_dist_pct") is not None
                else "—",
            )
        )
    if struct.get("poc") is not None:
        lines.append(
            S.MARKET_CTX_VP.format(
                poc=_fmt(struct.get("poc")),
                val=_fmt(struct.get("val")),
                vah=_fmt(struct.get("vah")),
            )
        )
    if struct.get("drawdown_from_high_pct") is not None:
        lines.append(
            S.MARKET_CTX_EXTENSION.format(
                dd=struct.get("drawdown_from_high_pct"),
                ru=struct.get("runup_from_low_pct"),
            )
        )
    if struct.get("btc_corr") is not None:
        lines.append(S.MARKET_CTX_BTC_CORR.format(corr=struct.get("btc_corr")))
    else:
        lines.append(f"BTC corr · {S.MARKET_CTX_UNAVAILABLE}")
    if struct.get("spread_pct") is not None:
        lines.append(S.MARKET_CTX_SPREAD.format(pct=struct.get("spread_pct")))
    else:
        lines.append(f"Spread · {S.MARKET_CTX_UNAVAILABLE}")
    return lines


def _fmt(raw: Any) -> str:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return "—"
    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:.4f}"
    return f"{value:.6f}"
