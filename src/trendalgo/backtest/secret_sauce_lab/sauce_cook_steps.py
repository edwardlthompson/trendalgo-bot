"""Per-helper cook steps for sauce_cook (Peer / Armed / Exit)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trendalgo.backtest.secret_sauce_lab.helper_pack import pack_helper_row
from trendalgo.device.sauce_names import SAUCE_ARMED, SAUCE_EXIT, SAUCE_PEER
from trendalgo.exchanges.fees import ExchangeFeeSchedule

EmitFn = Callable[[str], None]


def cook_peer_row(
    frame: Any,
    rows: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
    oracle_tf: str,
    n_swings: int,
    log: EmitFn,
) -> dict[str, Any] | None:
    from trendalgo.backtest.secret_sauce_lab.helper_peer_entry import cook_peer_helper
    from trendalgo.backtest.secret_sauce_lab.regime_peers import regime_matched_peer_hints
    from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime

    log("Secret Sauce Peer cooking…")
    structural = detect_regime(frame).structural
    regime_hints = regime_matched_peer_hints(rows, structural=structural)
    cook_rows = rows
    if regime_hints:
        preferred = {str(h.get("indicator") or "") for h in regime_hints}
        cook_rows = sorted(
            rows, key=lambda r: 0 if str(r.get("indicator") or "") in preferred else 1
        )
    packed = cook_peer_helper(
        frame, cook_rows, fee=fee, stake_usd=stake, oracle_swing_count=n_swings
    )
    if packed is None:
        return None
    d, reg, _tsl = packed
    row = pack_helper_row(
        d,
        reg,
        frame,
        fee=fee,
        stake=stake,
        symbol=symbol,
        timeframe=oracle_tf,
        indicator=SAUCE_PEER,
    )
    if row is not None:
        log(f"Secret Sauce Peer recorded ({row.get('net_pct')}%)")
    return row


def cook_armed_row(
    frame: Any,
    frames_by_tf: dict[str, Any],
    oracle: dict[str, Any],
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
    oracle_tf: str,
    n_swings: int,
    log: EmitFn,
) -> dict[str, Any] | None:
    from trendalgo.backtest.secret_sauce_lab.helper_armed import cook_armed_helper

    log("Secret Sauce Armed cooking…")
    o_frame = frames_by_tf.get(str(oracle.get("timeframe") or oracle_tf))
    packed = cook_armed_helper(
        frame, fee=fee, stake_usd=stake, oracle_tf_frame=o_frame, oracle_swing_count=n_swings
    )
    if packed is None:
        return None
    d, reg, _tsl = packed
    row = pack_helper_row(
        d,
        reg,
        frame,
        fee=fee,
        stake=stake,
        symbol=symbol,
        timeframe=oracle_tf,
        indicator=SAUCE_ARMED,
    )
    if row is not None:
        log(f"Secret Sauce Armed recorded ({row.get('net_pct')}%)")
    return row


def cook_exit_row(
    frame: Any,
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
    oracle_tf: str,
    n_swings: int,
    sauce_ta: dict[str, Any] | None,
    peer_row: dict[str, Any] | None,
    log: EmitFn,
) -> dict[str, Any] | None:
    from trendalgo.backtest.secret_sauce_lab.helper_exit import cook_exit_helper

    log("Secret Sauce Exit cooking…")
    packed = cook_exit_helper(
        frame,
        fee=fee,
        stake_usd=stake,
        sauce_ta_row=sauce_ta,
        peer_row=peer_row,
        oracle_swing_count=n_swings,
    )
    if packed is None:
        return None
    d, reg, _tsl = packed
    row = pack_helper_row(
        d,
        reg,
        frame,
        fee=fee,
        stake=stake,
        symbol=symbol,
        timeframe=oracle_tf,
        indicator=SAUCE_EXIT,
    )
    if row is not None:
        log(f"Secret Sauce Exit recorded ({row.get('net_pct')}%)")
    return row
