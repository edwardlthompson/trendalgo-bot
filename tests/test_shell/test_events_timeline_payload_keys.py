"""AV-G-RES4 — events surface JSON keys expected by Avalonia Bind."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_events import events_timeline_payload


def test_events_payload_keys_for_shell(tmp_path: Path) -> None:
    coin = {"pair": "ETH/USD", "symbol": "ETH", "spark_closes_30d": [2.0, 2.1]}
    payload = events_timeline_payload(tmp_path, coin, "ETH/USD")
    for key in ("title", "hint", "empty", "rows", "closes", "count", "estimated_label"):
        assert key in payload
