"""Render / compare README Exchange support table from support_matrix.json."""

from __future__ import annotations

from trendalgo.device.support_matrix import VenueSupport, load_support_matrix

START = "<!-- support-matrix:start -->"
END = "<!-- support-matrix:end -->"

_HEADER = (
    "| Venue | Portfolio | Public scan | Keyed scan | Deep OHLCV / BT | Live trade | Status |\n"
    "| --- | --- | --- | --- | --- | --- | --- |"
)

_WORLDWIDE = frozenset({"binance", "bybit", "okx"})


def cell_portfolio(v: VenueSupport) -> str:
    return _cell(v.portfolio)


def cell_cap(value: str) -> str:
    return _cell(value)


def readme_live_trade(v: VenueSupport) -> str:
    if v.live_trade == "base_only":
        return "Base only*"
    if v.live_trade != "yes":
        return "✗"
    if v.id in _WORLDWIDE:
        return "✓*"
    return "✓"


def _cell(value: str) -> str:
    text = str(value or "no").strip().lower()
    if text == "yes":
        return "✓"
    if text == "no":
        return "✗"
    if text == "partial":
        return "partial"
    if text == "wallet_lp":
        return "wallet/LP"
    if text == "thin":
        return "thin"
    if text == "base_only":
        return "base_only"
    return text


def render_exchange_support_table() -> str:
    lines = [_HEADER]
    for v in load_support_matrix():
        lines.append(
            f"| {v.brand} | {cell_portfolio(v)} | {cell_cap(v.public_scan)} | "
            f"{cell_cap(v.keyed_scan)} | {cell_cap(v.deep_ohlcv_bt)} | "
            f"{readme_live_trade(v)} | **{v.status_label}** |"
        )
    return "\n".join(lines) + "\n"


def extract_marked_block(text: str) -> str | None:
    if START not in text or END not in text:
        return None
    return text.split(START, 1)[1].split(END, 1)[0].strip("\n")
