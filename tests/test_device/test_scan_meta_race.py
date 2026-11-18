"""Prefs RMW: meta merge must not clobber UI filter prefs."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.lts_scan_model import load_filters
from trendalgo.device.scan_eta_filters import merge_scan_meta, write_filters_ui
from trendalgo.device.scan_model import device_scan_settings


def test_merge_scan_meta_preserves_volume_prefs(tmp_path: Path) -> None:
    write_filters_ui(
        tmp_path,
        {"min_volume_usd": 500_000, "require_continuous_1h": True},
    )
    merge_scan_meta(
        tmp_path,
        elapsed_s=12.5,
        funnel={
            "listed_n": 10,
            "after_volume_n": 5,
            "after_activity_n": 4,
            "qualified_n": 3,
            "min_volume_usd": 500_000,
            "require_continuous_1h": 1,
        },
    )
    saved = load_filters(tmp_path)
    assert saved["min_volume_usd"] == 500_000
    assert saved["require_continuous_1h"] is True
    settings = device_scan_settings(tmp_path)
    assert settings.min_uniformity == 0.0
    assert settings.min_volume_usd == 500_000.0

    write_filters_ui(tmp_path, {"min_volume_usd": 1})
    saved = load_filters(tmp_path)
    assert saved["min_volume_usd"] == 1
