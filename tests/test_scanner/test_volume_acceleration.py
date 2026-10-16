"""Vol Δ% matches upstream attach_volume_acceleration (1h, 24h vs prior daily baseline)."""

from __future__ import annotations

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.volume_acceleration import (
    apply_volume_acceleration,
    volume_acceleration_stats,
)


def _bars(volumes: list[float]) -> list[OhlcvPoint]:
    return [
        OhlcvPoint(time=1_700_000_000 + i * 3600, open=1.0, high=1.0, low=1.0, close=1.0, volume=v)
        for i, v in enumerate(volumes)
    ]


def test_doubled_last_24h_against_flat_week_is_plus_100_percent() -> None:
    stats = volume_acceleration_stats([100.0] * 216 + [200.0] * 24)
    assert stats is not None
    assert stats["volume_acceleration_pct"] == 100.0
    assert stats["volume_acceleration_window_days"] == 7
    assert stats["volume_recent_24h"] == 4800.0
    assert stats["volume_baseline_24h"] == 2400.0


def test_flat_volume_is_zero_percent() -> None:
    stats = volume_acceleration_stats([50.0] * 240)
    assert stats is not None
    assert stats["volume_acceleration_pct"] == 0.0


def test_short_history_has_no_value() -> None:
    assert volume_acceleration_stats([10.0] * 47) is None


def test_zero_baseline_has_no_value() -> None:
    assert volume_acceleration_stats([0.0] * 216 + [100.0] * 24) is None


def test_partial_week_uses_available_full_days_only() -> None:
    # 48 bars: current 24h + one full prior day as baseline.
    stats = volume_acceleration_stats([10.0] * 24 + [30.0] * 24)
    assert stats is not None
    assert stats["volume_acceleration_window_days"] == 1
    assert stats["volume_acceleration_pct"] == 200.0


def test_apply_sets_keys_and_clears_stale_values() -> None:
    coin: dict[str, object] = {"symbol": "SUI", "volume_acceleration_pct": 9.9}
    assert apply_volume_acceleration(coin, _bars([100.0] * 216 + [200.0] * 24)) is True
    assert coin["volume_acceleration_pct"] == 100.0
    assert apply_volume_acceleration(coin, _bars([1.0] * 10)) is False
    assert "volume_acceleration_pct" not in coin
    assert "volume_recent_24h" not in coin
