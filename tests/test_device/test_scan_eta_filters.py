"""Primary-filter ETA projection and last-scan meta."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.scan_eta_filters import (
    META_ELAPSED,
    META_FUNNEL,
    load_scan_meta,
    merge_scan_meta,
    preserve_scan_meta,
    projected_scan_coins,
)
from trendalgo.scanner.config import clamp_min_uniformity


def test_clamp_min_uniformity_always_off() -> None:
    assert clamp_min_uniformity(0) == 0.0
    assert clamp_min_uniformity(-1) == 0.0
    assert clamp_min_uniformity(0.2) == 0.0
    assert clamp_min_uniformity(0.22) == 0.0


def test_projected_scan_coins_fallback() -> None:
    assert projected_scan_coins(None, min_volume_usd=0, fallback_n=7) == 7


def test_projected_continuous_off_uses_after_volume() -> None:
    funnel = {
        "listed_n": 100,
        "after_volume_n": 40,
        "after_activity_n": 35,
        "qualified_n": 12,
        "min_volume_usd": 500_000,
    }
    n = projected_scan_coins(
        funnel,
        min_volume_usd=500_000,
        require_continuous_1h=False,
    )
    assert n == 40
    n_act = projected_scan_coins(
        funnel,
        min_volume_usd=500_000,
        require_continuous_1h=True,
    )
    assert n_act == 35


def test_projected_same_filters_uses_activity_base() -> None:
    funnel = {
        "listed_n": 100,
        "after_volume_n": 40,
        "after_activity_n": 40,
        "qualified_n": 12,
        "min_volume_usd": 500_000,
    }
    n = projected_scan_coins(funnel, min_volume_usd=500_000, require_continuous_1h=True)
    assert n == 40


def test_projected_lower_volume_raises_coins() -> None:
    funnel = {
        "listed_n": 200,
        "after_volume_n": 40,
        "after_activity_n": 40,
        "qualified_n": 12,
        "min_volume_usd": 1_000_000,
    }
    n = projected_scan_coins(funnel, min_volume_usd=100_000, require_continuous_1h=False)
    assert n > 40
    assert n <= 200


def test_merge_and_preserve_scan_meta(tmp_path: Path) -> None:
    merge_scan_meta(
        tmp_path,
        elapsed_s=125.4,
        funnel={
            "listed_n": 80,
            "after_volume_n": 30,
            "qualified_n": 10,
            "min_volume_usd": 500_000,
        },
    )
    meta = load_scan_meta(tmp_path)
    assert meta[META_ELAPSED] == 125.4
    assert isinstance(meta[META_FUNNEL], dict)
    assert meta[META_FUNNEL]["qualified_n"] == 10
    assert "min_uniformity" not in meta[META_FUNNEL]
    preserved = preserve_scan_meta(
        {"min_volume_usd": 1}, {META_ELAPSED: 9.0, META_FUNNEL: {"x": 1}}
    )
    assert preserved[META_ELAPSED] == 9.0
    assert preserved[META_FUNNEL] == {"x": 1}
