"""TradFi/FX daily 7d vs 30d sparks and gains must differ."""

from __future__ import annotations

from trendalgo.device.lts_scan_model import normalize_coin
from trendalgo.scanner.snapshot import OpportunityRow


def test_daily_board_sparks_and_gains_differ() -> None:
    # Rising then flat: 7d window ≠ 30d window.
    closes = [100.0 + i for i in range(30)]
    row = OpportunityRow(
        rank=1,
        pair="AAPL/USD",
        uniformity=1.0,
        gain_pct=0.1,
        volume_score=1e7,
        entry_signal=True,
        sparkline=closes,
    )
    from trendalgo.device.lts_scan_model import _basic_row

    basic = _basic_row(row)
    basic["exchange_id"] = "tradfi"
    coin = normalize_coin(basic)
    assert coin["spark_closes_7d"] != coin["spark_closes_30d"]
    assert len(coin["spark_closes_7d"]) == 7
    assert len(coin["spark_closes_30d"]) == 22
    assert coin["gains"]["7d"] != coin["gains"]["30d"]


def test_tradfi_keeps_daily_sparks_after_hourly_enrich() -> None:
    """1h enrich must not make 7d spark look like the full 30d series."""
    daily = [100.0 + i for i in range(30)]
    hourly = [100.0 + (i * 0.01) for i in range(200)]  # enough 1h bars to flip crypto path
    coin = normalize_coin(
        {
            "symbol": "AAPL",
            "pair": "AAPL/USD",
            "exchange_id": "tradfi",
            "chart_closes_1d": daily,
            "closes_1d": daily,
            "closes_1h": hourly,
            "chart_closes_1h": hourly,
        }
    )
    assert len(coin["spark_closes_7d"]) == 7
    assert len(coin["spark_closes_30d"]) == 22
    assert coin["spark_closes_7d"] != coin["spark_closes_30d"]
