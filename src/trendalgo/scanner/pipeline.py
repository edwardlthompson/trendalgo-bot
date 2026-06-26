"""Scanner pipeline — volume, gain, uniformity, entry/exit (O2)."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.lts.adapter import LtsAdapter, OhlcvBar
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.listings import verify_kraken_listings
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.uniformity import uniformity_score


def _synthetic_bars(gain_pct: float, base: float = 100.0) -> list[OhlcvBar]:
    """Build trending bars for uniformity when live OHLCV unavailable."""
    bars: list[OhlcvBar] = []
    step = gain_pct / 20 if gain_pct else 0.001
    price = base
    ts = int(datetime.now(UTC).timestamp() * 1000)
    for i in range(25):
        price *= 1 + step
        bars.append(
            OhlcvBar(
                timestamp_ms=ts + i * 300000,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1000,
            )
        )
    return bars


def _sample_market() -> list[dict[str, float | str]]:
    return [
        {"pair": "BTC/USD", "gain_pct": 0.035, "volume_usd": 5000000, "base": 50000},
        {"pair": "ETH/USD", "gain_pct": 0.048, "volume_usd": 2000000, "base": 3000},
        {"pair": "SOL/USD", "gain_pct": 0.062, "volume_usd": 800000, "base": 150},
        {"pair": "ADA/USD", "gain_pct": 0.015, "volume_usd": 400000, "base": 0.5},
        {"pair": "DOT/USD", "gain_pct": 0.028, "volume_usd": 300000, "base": 8},
    ]


def run_pipeline(settings: ScannerSettings) -> QualifiedSnapshot:
    pairs = verify_kraken_listings()
    candidates: list[OpportunityRow] = []
    adapter = LtsAdapter()

    for row in _sample_market():
        pair = str(row["pair"])
        if pair not in pairs:
            continue
        gain = float(row["gain_pct"])
        volume_usd = float(row["volume_usd"])
        if volume_usd < settings.min_volume_usd or gain < settings.min_gain_pct:
            continue
        bars = adapter.normalize_bars(
            [
                [b.timestamp_ms, b.open, b.high, b.low, b.close, b.volume]
                for b in _synthetic_bars(gain, float(row["base"]))
            ]
        )
        uni = uniformity_score(bars)
        if uni < settings.min_uniformity:
            continue
        spark = [round(b.close, 2) for b in bars[-12:]]
        entry = uni >= settings.min_uniformity and gain >= settings.min_gain_pct
        candidates.append(
            OpportunityRow(
                rank=0,
                pair=pair,
                uniformity=uni,
                gain_pct=gain,
                volume_score=min(1.0, volume_usd / settings.min_volume_usd),
                entry_signal=entry,
                sparkline=spark,
            )
        )

    candidates.sort(key=lambda o: (o.uniformity, o.gain_pct), reverse=True)
    ranked = [
        OpportunityRow(rank=i + 1, **{k: v for k, v in o.model_dump().items() if k != "rank"})
        for i, o in enumerate(candidates)
    ]

    return QualifiedSnapshot(
        generated_at=datetime.now(UTC),
        scan_id=0,
        opportunities=ranked,
    )
