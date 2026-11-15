"""Manual Sauce Pan job: Sauce-only on filtered Qualified coins with existing BT."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import load_lts_rows, save_lts_rows
from trendalgo.device.opportunity_sauce import oracle_rank_score, select_sauce_symbols
from trendalgo.device.scan_bt_prefs import load_scan_bt_prefs
from trendalgo.scanner.progress import get_scan_progress

__all__ = ["coins_eligible_for_sauce", "run_manual_sauce_pan"]


def coins_eligible_for_sauce(filtered: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtered Qualified coins that already have catalog BT strategy rows."""
    out: list[dict[str, Any]] = []
    for coin in filtered:
        rows = coin.get("backtest_top_strategies")
        if isinstance(rows, list) and rows:
            out.append(coin)
    return out


def _seed_rows(coin: dict[str, Any]) -> list[dict[str, Any]]:
    rows = coin.get("backtest_top_strategies")
    seed = list(rows) if isinstance(rows, list) else []
    for key in ("backtest_buy_hold", "backtest_oracle_max"):
        extra = coin.get(key)
        if isinstance(extra, dict) and extra:
            seed.append(dict(extra))
    return seed


def run_manual_sauce_pan(
    root: Path,
    filtered_coins: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cook Sauce on Oracle top-N of ``filtered_coins``; merge into full LTS board.

    Never runs catalog/deepen. Returns ``{ok, message, sauce_symbols, ...}``.
    """
    progress = get_scan_progress()
    prefs = load_scan_bt_prefs(root)
    top_n = int(prefs.sauce_top_n)
    eligible = coins_eligible_for_sauce(filtered_coins)
    if not eligible:
        msg = "Sauce Pan: no filtered coins with backtests"
        progress.log(msg, level="warn")
        return {"ok": False, "message": msg, "sauce_symbols": []}

    seed_by_sym: dict[str, list[dict[str, Any]]] = {}
    scored: list[tuple[str, float]] = []
    coin_by_sym: dict[str, dict[str, Any]] = {}
    for coin in eligible:
        sym = str(coin.get("symbol") or "").strip().upper()
        if not sym:
            continue
        seed = _seed_rows(coin)
        if not seed:
            continue
        seed_by_sym[sym] = seed
        scored.append((sym, oracle_rank_score(seed)))
        coin_by_sym[sym] = coin

    sauce_syms = select_sauce_symbols(scored, top_n=top_n)
    sauce_coins = [coin_by_sym[s] for s in sauce_syms if s in coin_by_sym]
    if not sauce_coins:
        msg = "Sauce Pan: no Oracle-ranked pairs to cook"
        progress.log(msg, level="warn")
        return {"ok": False, "message": msg, "sauce_symbols": []}

    progress.log(
        f"Sauce Pan manual: {len(sauce_coins)} of {len(eligible)} eligible "
        f"(top{top_n}; {', '.join(sauce_syms)}) — Sauce-only, no catalog"
    )
    from trendalgo.device.scanner_all_ta_bt import run_opportunity_sauce_pass

    summary = run_opportunity_sauce_pass(
        sauce_coins,
        prefs_root=root,
        seed_rows_by_symbol=seed_by_sym,
        top_n=top_n,
    )
    if not isinstance(summary, dict):
        msg = "Sauce Pan: Sauce pass returned nothing"
        progress.log(msg, level="error")
        return {"ok": False, "message": msg, "sauce_symbols": sauce_syms}

    from trendalgo.lts_vendor.bridge import merge_backtest_into_coins

    board = load_lts_rows(root)
    if not board:
        board = list(filtered_coins)
    sauced_keys = {str(s).strip().upper() for s in summary.get("sauce_symbols") or sauce_syms}
    targets = [c for c in board if str(c.get("symbol") or "").strip().upper() in sauced_keys]
    if not targets:
        targets = list(sauce_coins)
    updated = merge_backtest_into_coins(targets, summary)
    by_upd = {str(c.get("symbol") or "").strip().upper(): c for c in updated}
    for i, coin in enumerate(board):
        key = str(coin.get("symbol") or "").strip().upper()
        if key in by_upd:
            board[i] = by_upd[key]
    save_lts_rows(root, board)
    progress.log(
        f"Sauce Pan merge done: {len(by_upd)} coins updated · "
        f"sauced={', '.join(sorted(sauced_keys)) or 'none'}"
    )
    return {
        "ok": True,
        "message": "ok",
        "sauce_symbols": list(summary.get("sauce_symbols") or sauce_syms),
        "sauce_top_n": top_n,
        "coins_updated": len(by_upd),
    }
