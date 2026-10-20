"""Heuristic portfolio category totals (stablecoins / tokens / fiat / other)."""

from __future__ import annotations

from typing import Any

_STABLE = frozenset(
    {
        "USDT",
        "USDC",
        "USD",
        "DAI",
        "BUSD",
        "TUSD",
        "USDD",
        "FRAX",
        "GUSD",
        "USDP",
        "USDG",
    }
)
_FIAT = frozenset({"USD", "EUR", "GBP", "JPY", "CAD", "AUD"})
# Scanner excludes these bases (USDC/USD, USDT/USD, …) — not the USD quote.
_STABLE_BASES = frozenset(s for s in _STABLE if s != "USD")


def is_stablecoin_base(pair_or_symbol: str) -> bool:
    """True when the asset base is a stablecoin (e.g. USDC of USDC/USD)."""
    sym = (pair_or_symbol or "").upper().split("/")[0].split("-")[0].strip()
    return bool(sym) and sym in _STABLE_BASES


def categorize_holding(asset: str) -> str:
    sym = (asset or "").upper().split("/")[0].split("-")[0]
    if sym in _FIAT:
        return "Fiat"
    if sym in _STABLE:
        return "Stablecoins"
    return "Tokens"


def category_totals(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, float] = {
        "Tokens": 0.0,
        "Stablecoins": 0.0,
        "DeFi": 0.0,
        "Fiat": 0.0,
    }
    for row in holdings:
        asset = str(row.get("asset") or "")
        value = float(row.get("value_usd") or 0.0)
        buckets[categorize_holding(asset)] += value
    total = sum(buckets.values()) or 1.0
    rows = [
        {"category": name, "value_usd": round(val, 2), "pct": round(100.0 * val / total, 2)}
        for name, val in buckets.items()
    ]
    # Honest empty: NFTs are not valued yet — never show $0 as if complete.
    rows.append(
        {
            "category": "NFTs",
            "value_usd": None,
            "pct": None,
            "status": "untracked",
        }
    )
    return rows


def cash_drag_pct(holdings: list[dict[str, Any]]) -> float:
    total = sum(float(h.get("value_usd") or 0.0) for h in holdings) or 1.0
    cash = sum(
        float(h.get("value_usd") or 0.0)
        for h in holdings
        if categorize_holding(str(h.get("asset") or "")) in {"Fiat", "Stablecoins"}
    )
    return round(100.0 * cash / total, 2)


def concentration_top_pct(holdings: list[dict[str, Any]], n: int = 1) -> float:
    values = sorted((float(h.get("value_usd") or 0.0) for h in holdings), reverse=True)
    total = sum(values) or 1.0
    return round(100.0 * sum(values[:n]) / total, 2)
