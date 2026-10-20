"""LTS public snapshot + bridge smoke tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trendalgo.lts_vendor.bridge import (
    merge_backtest_into_coins,
    opportunities_to_final_results,
    publish_from_v2_snapshot,
)
from trendalgo.lts_vendor.public_snapshot import load_public_snapshot, write_public_snapshot
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BACKTEST_ENABLED", "0")
    return tmp_path


def _sample_snap() -> QualifiedSnapshot:
    return QualifiedSnapshot(
        version="2",
        generated_at=datetime.now(UTC),
        as_of=datetime.now(UTC),
        scan_id=1,
        degraded=False,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.8,
                gain_pct=0.05,
                volume_score=1_000_000,
                entry_signal=True,
                sparkline=[100.0, 101.0, 102.5, 103.0],
            )
        ],
    )


def test_load_seeds_fixture(data_dir: Path) -> None:
    payload = load_public_snapshot()
    assert payload["schema_version"] == 1
    assert isinstance(payload["coins"], list)
    assert (data_dir / "qualified_public_snapshot.json").is_file()


def test_publish_without_backtest_writes_coins(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from trendalgo.market.types import OhlcvPoint

    base = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())

    def fake_fetch(pair: str, timeframe: str, since: object, until: object, **kwargs: object):
        n = 180 if timeframe == "1h" else 30
        step = 3600 if timeframe == "1h" else 86400
        return [
            OhlcvPoint(
                time=base + i * step,
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.0 + i,
                volume=1.0,
            )
            for i in range(n)
        ]

    monkeypatch.setattr("trendalgo.market.kraken.fetch_ohlcv", fake_fetch)
    payload = publish_from_v2_snapshot(_sample_snap(), run_backtests=False)
    assert len(payload["coins"]) == 1
    coin = payload["coins"][0]
    assert coin["symbol"] == "BTC"
    assert len(coin["closes_1h"]) == 180
    assert len(coin["closes_1d"]) == 30
    # Real OHLCV gains from trimmed 1h window — not daily[-30:] or scan sparkline.
    assert coin["gains"]["7d"] == pytest.approx(((279.0 / 112.0) - 1.0) * 100.0)
    assert coin["gains"]["30d"] == pytest.approx(((279.0 / 100.0) - 1.0) * 100.0)


def test_merge_backtest_fields_shape(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.market.types import OhlcvPoint

    def fake_fetch(pair: str, timeframe: str, since: object, until: object, **kwargs: object):
        return [
            OhlcvPoint(time=1_700_000_000 + i, open=1, high=1, low=1, close=100.0 + i, volume=1)
            for i in range(20 if timeframe == "1d" else 170)
        ]

    monkeypatch.setattr("trendalgo.market.kraken.fetch_ohlcv", fake_fetch)
    coins = opportunities_to_final_results(_sample_snap())
    summary = {
        "results": [
            {
                "symbol": "BTC",
                "indicator": "RSI",
                "timeframe": "1h",
                "params": {"period": 14},
                "trailing_stop_loss_pct": 6.0,
                "net_pct": 12.0,
                "trades": 3,
                "win_pct": 66.0,
                "final_equity": 1120.0,
            },
            {
                "symbol": "BTC",
                "indicator": "B&H",
                "timeframe": "1h",
                "params": {},
                "net_pct": 5.0,
                "final_equity": 1050.0,
            },
        ]
    }
    merge_backtest_into_coins(coins, summary)
    assert coins[0]["backtest_top_strategies"]
    assert coins[0]["backtest_buy_hold"] is not None
    write_public_snapshot(
        {
            "schema_version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "field_set": "full",
            "scan_interval_seconds": 900,
            "coins": coins,
        }
    )
    loaded = load_public_snapshot()
    assert loaded["coins"][0]["backtest_top_strategies"]
