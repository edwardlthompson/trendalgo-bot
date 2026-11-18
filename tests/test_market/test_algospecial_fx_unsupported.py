"""AlgoSpecial 404 unsupported persist + partition."""

from __future__ import annotations

from pathlib import Path

from trendalgo.market.algospecial_fx_unsupported import (
    load_unsupported,
    mark_unsupported,
    partition_supported,
)


def test_seed_includes_known_404_exotics(tmp_path: Path) -> None:
    blocked = load_unsupported(tmp_path)
    assert "USD/ARS" in blocked
    assert "EUR/TRY" in blocked
    assert "EUR/USD" not in blocked


def test_mark_and_partition(tmp_path: Path) -> None:
    mark_unsupported(tmp_path, "USD/SEK")
    live, skipped = partition_supported(tmp_path, ["EUR/USD", "USD/SEK", "GBP/USD"])
    assert live == ["EUR/USD", "GBP/USD"]
    assert "USD/SEK" in skipped
