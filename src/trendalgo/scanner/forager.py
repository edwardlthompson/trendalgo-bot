"""Dynamic pair forager — LTS listings + volume heuristics (T25, T28)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from trendalgo.scanner.config import ScannerSettings, default_scanner_settings
from trendalgo.scanner.listings import verify_kraken_listings
from trendalgo.scanner.pipeline import _sample_market


def forage_pairs(settings: ScannerSettings | None = None, *, top_n: int = 8) -> dict[str, object]:
    """Rank tradable pairs by volume and momentum heuristics."""
    settings = settings or default_scanner_settings()
    listings = set(verify_kraken_listings())
    scored: list[dict[str, object]] = []

    for row in _sample_market():
        pair = str(row["pair"])
        if pair not in listings:
            continue
        gain = float(row["gain_pct"])
        volume_usd = float(row["volume_usd"])
        if volume_usd < settings.min_volume_usd * 0.5:
            continue
        volume_score = min(1.0, volume_usd / max(settings.min_volume_usd, 1))
        momentum_score = min(1.0, gain / max(settings.min_gain_pct, 0.001))
        composite = round(0.6 * volume_score + 0.4 * momentum_score, 4)
        scored.append(
            {
                "pair": pair,
                "volume_usd": volume_usd,
                "gain_pct": gain,
                "volume_score": round(volume_score, 4),
                "momentum_score": round(momentum_score, 4),
                "forager_score": composite,
                "source": "lts_volume_heuristic",
            }
        )

    scored.sort(
        key=lambda r: float(cast(float | int | str, r.get("forager_score", 0))), reverse=True
    )
    picks = scored[:top_n]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "pair_count": len(picks),
        "pairs": picks,
        "prototype": True,
    }
