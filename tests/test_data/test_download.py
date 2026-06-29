"""Tests for trendalgo.data stubs and CSV helpers."""

from __future__ import annotations

from pathlib import Path

from trendalgo.data.download import save_csv
from trendalgo.data.onchain_sentiment import onchain_sentiment_stub


def test_onchain_sentiment_stub_deterministic() -> None:
    a = onchain_sentiment_stub("btc")
    b = onchain_sentiment_stub("BTC")
    assert a["asset"] == "BTC"
    assert a == b
    assert a["paid_indexers"] is False
    assert 0 <= a["onchain_activity_score"] <= 1


def test_save_csv_writes_header_and_rows(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "sample.csv"
    rows = [[1_700_000_000_000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    save_csv(rows, out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("timestamp,open,high,low,close,volume\n")
    assert "1.5" in text
