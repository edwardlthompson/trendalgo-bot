"""S5–S6 Final packing + silent helper feeds for sauce_cook."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trendalgo.backtest.secret_sauce_lab.helper_pack import pack_helper_row
from trendalgo.device.sauce_names import SAUCE_EXIT, SAUCE_FINAL
from trendalgo.exchanges.fees import ExchangeFeeSchedule

EmitFn = Callable[[str], None]


def silent_s6_helpers(
    frame: Any,
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
    oracle_tf: str,
    n_swings: int,
    swings: list[Any],
    published: list[dict[str, Any]],
    sauce_ta: dict[str, Any] | None,
    peer_row: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Teacher / genetic / MFE pack under `_sauce_*` for Final only."""
    out: list[dict[str, Any]] = []
    try_cooks: list[tuple[str, Callable[[], tuple[Any, Any, float] | None]]] = [
        ("teacher", lambda: _teacher(frame, swings, fee, stake)),
        ("genetic", lambda: _genetic(frame, fee, stake, n_swings)),
        ("mfe", lambda: _mfe(frame, published, sauce_ta, peer_row, fee, stake, n_swings)),
    ]
    for name, cook in try_cooks:
        try:
            packed = cook()
        except (TypeError, ValueError, KeyError, IndexError):
            continue
        if packed is None:
            continue
        d, reg, _tsl = packed
        row = pack_helper_row(
            d,
            reg,
            frame,
            fee=fee,
            stake=stake,
            symbol=symbol,
            timeframe=oracle_tf,
            indicator=f"_sauce_{name}",
        )
        if row is not None:
            out.append(row)
    return out


def cook_final_row(
    frame: Any,
    helpers: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
    oracle_tf: str,
    n_swings: int,
    log: EmitFn,
) -> dict[str, Any] | None:
    from trendalgo.backtest.secret_sauce_lab.final_boss import cook_final_boss
    from trendalgo.backtest.secret_sauce_lab.vol_targeting import vol_target_scalar

    log("Secret Sauce Final cooking…")
    packed = cook_final_boss(frame, helpers, fee=fee, stake_usd=stake, oracle_swing_count=n_swings)
    if packed is None:
        return None
    d, reg, tsl, voters = packed
    extra: dict[str, Any] = {
        "final_voters": voters,
        "vol_target_scalar": vol_target_scalar(frame),
    }
    try:
        from trendalgo.backtest.secret_sauce_features import (
            entries_for_secret_sauce,
            exits_for_secret_sauce,
        )
        from trendalgo.backtest.secret_sauce_lab.scale_out import scale_out_proxy_net

        extra["scale_out"] = scale_out_proxy_net(
            frame,
            entries_for_secret_sauce(frame, d.rule),
            exits_for_secret_sauce(frame, d.exit_rule),
            fee=fee,
            stake_usd=stake,
            trailing_stop_pct=float(tsl or 0.0),
        )
    except (TypeError, ValueError, KeyError, IndexError):
        pass
    row = pack_helper_row(
        d,
        reg,
        frame,
        fee=fee,
        stake=stake,
        symbol=symbol,
        timeframe=oracle_tf,
        indicator=SAUCE_FINAL,
        extra=extra,
    )
    if row is not None:
        log(f"Secret Sauce Final recorded ({row.get('net_pct')}%) voters={voters}")
    return row


def _teacher(
    frame: Any, swings: list[Any], fee: ExchangeFeeSchedule, stake: float
) -> tuple[Any, Any, float] | None:
    from trendalgo.backtest.secret_sauce_lab.teacher_distill import cook_teacher_distill

    return cook_teacher_distill(frame, swings, fee=fee, stake_usd=stake)


def _genetic(
    frame: Any, fee: ExchangeFeeSchedule, stake: float, n: int
) -> tuple[Any, Any, float] | None:
    from trendalgo.backtest.secret_sauce_lab.genetic_search import cook_genetic

    return cook_genetic(frame, fee=fee, stake_usd=stake, oracle_swing_count=n)


def _mfe(
    frame: Any,
    published: list[dict[str, Any]],
    ta: dict[str, Any] | None,
    peer: dict[str, Any] | None,
    fee: ExchangeFeeSchedule,
    stake: float,
    n: int,
) -> tuple[Any, Any, float] | None:
    from trendalgo.backtest.secret_sauce_lab.mfe_exit import cook_mfe_exit

    seed = next((r for r in published if r.get("indicator") == SAUCE_EXIT), None) or ta or peer
    return cook_mfe_exit(frame, seed, fee=fee, stake_usd=stake, oracle_swing_count=n)
