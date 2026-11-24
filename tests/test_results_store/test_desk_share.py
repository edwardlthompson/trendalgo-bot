"""Headless board/strategy PNG share."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from trendalgo.results_store.desk_share import share_board_png, share_strategy_png  # noqa: E402


def test_share_board_png_writes_file(tmp_path: Path) -> None:
    (tmp_path / "lts_scan_rows.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair": "BTC/USD",
                        "exchange": "kraken",
                        "gain": 3.2,
                        "volume_score": 1.0,
                        "health": "A",
                    },
                    {
                        "pair": "ETH/USD",
                        "exchange": "kraken",
                        "gain": 1.1,
                        "volume_score": 0.5,
                        "health": "B",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    out = share_board_png(
        tmp_path,
        lane="crypto",
        pairs=["ETH/USD", "BTC/USD"],
        title="Scanner · 2 pairs",
    )
    path = Path(out["path"])
    assert path.is_file()
    assert path.suffix.lower() == ".png"
    assert path.stat().st_size > 50
    assert out["rows"] == 2


def test_share_strategy_png_empty_pair_ok(tmp_path: Path) -> None:
    out = share_strategy_png(tmp_path, pair="ETH/USD")
    path = Path(out["path"])
    assert path.is_file()
    assert out["pair"] == "ETH/USD"
