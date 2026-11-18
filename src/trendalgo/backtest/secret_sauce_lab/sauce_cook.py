"""Orchestrate Core Lab + helpers + Final Boss (uncapped Sauce cook)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trendalgo.backtest.secret_sauce_lab.sauce_cook_extra import cook_final_row, silent_s6_helpers
from trendalgo.backtest.secret_sauce_lab.sauce_cook_steps import (
    cook_armed_row,
    cook_exit_row,
    cook_peer_row,
)
from trendalgo.device.sauce_names import SAUCE_LAB, SAUCE_PEER
from trendalgo.exchanges.fees import ExchangeFeeSchedule

EmitFn = Callable[[str], None]


def cook_sauce_suite(
    *,
    oracle: dict[str, Any],
    rows: list[dict[str, Any]],
    frames_by_tf: dict[str, Any],
    symbol: str,
    stake: float,
    fee: ExchangeFeeSchedule,
    core_lab: dict[str, Any] | None,
    sauce_ta: dict[str, Any] | None,
    emit: EmitFn | None = None,
) -> list[dict[str, Any]]:
    """Return helper + Final rows (Core Lab passed in already refined)."""
    log: EmitFn = emit or (lambda _m: None)
    swings = list(oracle.get("oracle_swings") or [])
    oracle_tf = str(oracle.get("timeframe") or "1h")
    frame = frames_by_tf.get(oracle_tf)
    if frame is None:
        for tf in ("1h", "2h", "4h", "8h"):
            if frames_by_tf.get(tf) is not None:
                frame, oracle_tf = frames_by_tf[tf], tf
                break
    if frame is None or getattr(frame, "empty", True):
        return []
    n_swings = len(swings)
    out: list[dict[str, Any]] = []
    try:
        row = cook_peer_row(
            frame,
            rows,
            fee=fee,
            stake=stake,
            symbol=symbol,
            oracle_tf=oracle_tf,
            n_swings=n_swings,
            log=log,
        )
        if row is not None:
            out.append(row)
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        log(f"Secret Sauce Peer soft-fail: {exc}")
    try:
        row = cook_armed_row(
            frame,
            frames_by_tf,
            oracle,
            fee=fee,
            stake=stake,
            symbol=symbol,
            oracle_tf=oracle_tf,
            n_swings=n_swings,
            log=log,
        )
        if row is not None:
            out.append(row)
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        log(f"Secret Sauce Armed soft-fail: {exc}")
    peer_row = next((r for r in out if r.get("indicator") == SAUCE_PEER), None)
    try:
        row = cook_exit_row(
            frame,
            fee=fee,
            stake=stake,
            symbol=symbol,
            oracle_tf=oracle_tf,
            n_swings=n_swings,
            sauce_ta=sauce_ta,
            peer_row=peer_row,
            log=log,
        )
        if row is not None:
            out.append(row)
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        log(f"Secret Sauce Exit soft-fail: {exc}")

    silent = silent_s6_helpers(
        frame,
        fee=fee,
        stake=stake,
        symbol=symbol,
        oracle_tf=oracle_tf,
        n_swings=n_swings,
        swings=swings,
        published=out,
        sauce_ta=sauce_ta,
        peer_row=peer_row,
    )
    helpers: list[dict[str, Any]] = [*(x for x in (core_lab, sauce_ta) if x), *out, *silent]
    try:
        from trendalgo.backtest.secret_sauce_lab.meta_tsl import apply_meta_tsl_to_helpers

        helpers = apply_meta_tsl_to_helpers(frame, helpers, fee=fee, stake_usd=stake)
        by_ind = {str(r.get("indicator")): r for r in helpers}
        out = [by_ind.get(str(r.get("indicator")), r) for r in out]
    except (TypeError, ValueError, KeyError, IndexError):
        pass

    try:
        row = cook_final_row(
            frame,
            helpers,
            fee=fee,
            stake=stake,
            symbol=symbol,
            oracle_tf=oracle_tf,
            n_swings=n_swings,
            log=log,
        )
        if row is not None:
            out.append(row)
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        log(f"Secret Sauce Final soft-fail: {exc}")

    try:
        from trendalgo.backtest.secret_sauce_lab.dual_horizon import cook_dual_horizon

        dual = cook_dual_horizon(
            frames_by_tf,
            oracle_tf=str(oracle.get("timeframe") or oracle_tf),
            oracle_trades=swings,
            fee=fee,
            stake=stake,
            symbol=symbol,
        )
        if (
            dual is not None
            and core_lab is not None
            and float(dual.get("net_pct") or float("-inf"))
            > float(core_lab.get("net_pct") or float("-inf"))
        ):
            dual["indicator"] = SAUCE_LAB
            out.append(dual)
            log(f"Dual-horizon Core refresh ({dual.get('net_pct')}%)")
    except (TypeError, ValueError, KeyError, IndexError):
        pass
    return out
