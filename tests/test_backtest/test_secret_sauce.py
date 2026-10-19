"""Secret Sauce miner, entry+exit eval, validate, compact params."""

from __future__ import annotations

import pandas as pd

from trendalgo.backtest.secret_sauce_mine import (
    entries_for_secret_sauce,
    is_secret_sauce_indicator,
    mine_secret_sauce,
)
from trendalgo.backtest.secret_sauce_validate import validate_secret_sauce
from trendalgo.backtest.ta_fleet import backtest_one, buy_and_hold_row, oracle_max_row
from trendalgo.backtest.ta_simulator import simulate_oracle_max_gain
from trendalgo.device.backtest_results_ui import format_export_params
from trendalgo.device.scanner_chart_trades import regions_from_oracle_swings
from trendalgo.device.strings import SECRET_SAUCE_PARAMS_STUB
from trendalgo.exchanges.fees import ExchangeFeeSchedule
from trendalgo.lts_vendor.backtesting.report import notification_rows_for_symbol


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=0.0,
        maker_pct=0.0,
        tier="retail",
        source_url="",
    )


def _valley_frame(*, n_swings: int = 4, volume_spikes: bool = False) -> pd.DataFrame:
    # Repeat trough→peak pattern so walk-forward has train + holdout.
    chunk = [
        (100, 101, 99, 100, 10.0),
        (100, 102, 98, 99, 12.0),
        (99, 100, 90, 91, 80.0 if volume_spikes else 11.0),  # trough / high vol
        (91, 110, 90, 108, 40.0 if volume_spikes else 10.0),
        (108, 120, 107, 119, 90.0 if volume_spikes else 11.0),  # peak / high vol
        (119, 119, 100, 101, 15.0),
    ]
    rows: list[tuple[float, float, float, float, float]] = []
    for _ in range(n_swings):
        rows.extend(chunk)
    rows.append((100, 101, 99, 100, 10.0))
    return pd.DataFrame(
        [{"open": o, "high": h, "low": low, "close": c, "volume": v} for o, h, low, c, v in rows]
    )


def test_mine_secret_sauce_entry_and_exit() -> None:
    df = _valley_frame(volume_spikes=True)
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    dossier = mine_secret_sauce(df, oracle_trades=list(stats["oracle_swings"]))
    assert dossier is not None
    assert dossier.rule.conjuncts
    assert dossier.exit_rule.conjuncts
    assert dossier.rule.requires_backtest is True
    formula = dossier.formula_en.lower()
    assert "enter when" in formula
    assert "exit when" in formula
    mask = entries_for_secret_sauce(df, dossier.rule)
    assert mask.any()
    assert len(dossier.swing_hits) == len(dossier.oracle_entry_indexes)
    assert len(dossier.exit_hits) == len(dossier.oracle_exit_indexes)


def test_spectrum_oracle_gt_sauce_gt_bh() -> None:
    df = _valley_frame(n_swings=5, volume_spikes=True)
    fee = _fee()
    stake = 1000.0
    oracle = oracle_max_row(df, lookback_seconds=0, stake_usd=stake, fee=fee)
    bh = buy_and_hold_row(df, lookback_seconds=0, stake_usd=stake, fee=fee)
    assert oracle is not None and bh is not None
    dossier = mine_secret_sauce(df, oracle_trades=list(oracle["oracle_swings"]))
    assert dossier is not None
    trial, reason = backtest_one(
        df,
        dossier.rule.strategy_id,
        fee,
        stake,
        timeframe="1h",
        lookback_seconds=0,
        params=dossier.eval_params(),
        phase="secret_sauce",
    )
    assert trial is not None, reason
    oracle_net = float(oracle["net_profit"]) / stake * 100.0
    bh_net = float(bh["net_profit"]) / stake * 100.0
    sauce_net = float(trial["net_profit"]) / stake * 100.0
    assert oracle_net > sauce_net > bh_net
    ok, msg = validate_secret_sauce(
        dossier,
        df,
        {"net_pct": sauce_net},
        fee=fee,
        stake_usd=stake,
        oracle_net=oracle_net,
        peer_net=bh_net,
    )
    assert ok, msg
    row = {
        "indicator": "Secret Sauce",
        "params": {**dossier.eval_params(), "heartbeat_dossier": dossier.to_dict()},
        "heartbeat_dossier": dossier.to_dict(),
    }
    assert format_export_params(row) == SECRET_SAUCE_PARAMS_STUB
    assert len(format_export_params(row)) < 40


def test_is_secret_sauce_indicator() -> None:
    assert is_secret_sauce_indicator("Secret Sauce")
    assert is_secret_sauce_indicator("Secret Sauce Lab")
    assert is_secret_sauce_indicator("Secret Sauce TA")
    assert is_secret_sauce_indicator("GEN_SECRET_1")
    assert not is_secret_sauce_indicator("Oracle max")
    assert not is_secret_sauce_indicator("RSI")


def test_trend_feature_and_pair_seeds() -> None:
    from trendalgo.backtest.secret_sauce_features import causal_features
    from trendalgo.backtest.secret_sauce_seeds import classic_pair_seeds

    df = _valley_frame(n_swings=3)
    feats = causal_features(df)
    assert "above_sma50" in feats[0]
    pairs = classic_pair_seeds("GEN_SECRET_1")
    assert any(any(c.feature == "above_sma50" for c in er.conjuncts) for er, _xr in pairs)


def test_regions_from_oracle_swings() -> None:
    df = _valley_frame(n_swings=2)
    idx = pd.date_range("2026-01-01", periods=len(df), freq="h", tz="UTC")
    df = df.copy()
    df.index = idx
    stats = simulate_oracle_max_gain(df, stake_usd=1000.0, fee=_fee())
    assert stats is not None
    regions = regions_from_oracle_swings(df, list(stats["oracle_swings"]))
    assert regions
    assert all(r.get("entry_time") for r in regions)


def test_notification_rows_peel_oracle() -> None:
    summary = {
        "results": [
            {"symbol": "ETH", "indicator": "B&H", "net_pct": 10.0},
            {
                "symbol": "ETH",
                "indicator": "Oracle max",
                "net_pct": 90.0,
                "oracle_swings": [{"x": 1}],
            },
            {"symbol": "ETH", "indicator": "Secret Sauce", "net_pct": 40.0},
            {"symbol": "ETH", "indicator": "RSI", "net_pct": 12.0},
        ]
    }
    details = notification_rows_for_symbol(summary, "ETH", top_n=50)
    inds = {str(r.get("indicator")) for r in details["top_strategies"]}
    assert "Oracle max" not in inds
    assert "Secret Sauce" in inds
    assert details["oracle_max"]["net_pct"] == 90.0
    assert details["buy_hold"]["net_pct"] == 10.0


def test_concurrent_mine_helper() -> None:
    from trendalgo.device.pair_strategy_secret_sauce import mine_and_eval_secret_sauce

    df = _valley_frame(n_swings=4, volume_spikes=True)
    fee = _fee()
    stake = 1000.0
    oracle = oracle_max_row(df, lookback_seconds=0, stake_usd=stake, fee=fee)
    assert oracle is not None
    oracle = dict(oracle)
    oracle["timeframe"] = "1h"
    from trendalgo.device.scanner_all_ta_prune import fleet_row_to_lts

    o_lts = fleet_row_to_lts(oracle, symbol="BTC", stake_usd=stake, is_oracle=True)
    row = mine_and_eval_secret_sauce(
        o_lts,
        frames_by_tf={"1h": df},
        symbol="BTC",
        stake=stake,
        fee=fee,
    )
    assert row is not None
    assert str(row.get("indicator")) == "Secret Sauce Lab"
    assert isinstance(row.get("heartbeat_dossier"), dict)
    formula = str(row["heartbeat_dossier"].get("formula_en") or "").lower()
    assert "enter when" in formula and "exit when" in formula
