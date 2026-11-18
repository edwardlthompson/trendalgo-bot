"""TEMP debug force-fresh scan helpers."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.debug_scan import (
    ENV_FLAG,
    clear_scan_caches,
    debug_scan_enabled,
)
from trendalgo.device.lts_scan_model import LTS_ROWS_FILE, save_lts_rows


def test_debug_scan_enabled(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv(ENV_FLAG, raising=False)
    assert debug_scan_enabled() is False
    monkeypatch.setenv(ENV_FLAG, "1")
    assert debug_scan_enabled() is True


def test_clear_scan_caches_drops_rows_and_sets_cache_hours(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    save_lts_rows(tmp_path, [{"symbol": "BTC", "pair": "BTC/USD"}])
    rows = tmp_path / LTS_ROWS_FILE
    assert rows.is_file()
    cache = tmp_path / "lts_price_cache.db"
    cache.write_bytes(b"x")
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    cleared = clear_scan_caches(tmp_path)
    assert LTS_ROWS_FILE in cleared
    assert "lts_price_cache.db" in cleared
    assert not rows.exists()
    assert not cache.exists()
    assert __import__("os").environ.get("CACHE_PRICE_HOURS") == "0"
