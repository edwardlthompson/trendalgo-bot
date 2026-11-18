"""I — peer inspire filtered to same regime structural bucket."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.secret_sauce_lab.catalog_reseed import peer_hints_from_rows


def regime_matched_peer_hints(
    rows: list[dict[str, Any]],
    *,
    structural: str,
    prefer_osc: bool = True,
) -> list[dict[str, Any]]:
    """Prefer peers whose stamped regime.structural matches; else fall back to all hints."""
    matched: list[dict[str, Any]] = []
    for r in rows:
        reg = r.get("regime") if isinstance(r.get("regime"), dict) else None
        if reg and str(reg.get("structural") or "") == structural:
            matched.append(r)
    pool = matched if matched else rows
    hints = peer_hints_from_rows(pool, preferred_tf="", prefer_osc=prefer_osc)
    if not hints:
        hints = peer_hints_from_rows(
            pool, preferred_tf="", prefer_osc=prefer_osc, require_beat_bh=False
        )
    return hints
