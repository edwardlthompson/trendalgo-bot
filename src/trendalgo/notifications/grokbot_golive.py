"""Advisory go-live readiness from the dry-run journal. Never approves live trading."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.notifications.grokbot_payload import envelope
from trendalgo.risk.journal import TradeJournal

_TRUE = frozenset({"1", "true", "yes", "on"})


def journal_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    equity = peak = max_dd = max_dd_pct = 0.0
    streak = max_streak = sells = 0
    last_at = ""
    for row in reversed(trades):
        stamp = str(row.get("created_at") or "")
        if stamp:
            last_at = stamp
        if str(row.get("side") or "").lower() not in {"sell", "short"}:
            continue
        sells += 1
        pnl = float(row.get("pnl_usd") or 0)
        equity += pnl
        peak = max(peak, equity)
        dd = peak - equity
        if dd > max_dd:
            max_dd, max_dd_pct = dd, (dd / peak if peak else 0.0)
        if pnl < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trade_count": len(trades),
        "sell_count": sells,
        "pnl_usd": round(equity, 4),
        "max_drawdown_usd": round(max_dd, 4),
        "max_drawdown_pct": round(max_dd_pct, 4),
        "max_losing_streak": max_streak,
        "current_losing_streak": streak,
        "last_trade_at": last_at or None,
    }


def fee_assumptions() -> dict[str, float]:
    return {
        "backtest_fee_bps_round_trip": _env_float("BACKTEST_FEE_BPS_ROUND_TRIP", 52.0),
        "dry_run_slippage_bps": _env_float("DRY_RUN_SLIPPAGE_BPS", 0.0),
        "dex_max_slippage_bps": _env_float("DEX_MAX_SLIPPAGE_BPS", 100.0),
    }


def stale_flags(*, last_trade_at: str | None, now: datetime) -> dict[str, Any]:
    warnings: list[str] = []
    hours = _age_hours(last_trade_at, now)
    if hours is not None and hours > 168:
        warnings.append("last dry-run trade older than 7 days")
    if os.environ.get("TRENDALGO_MARKET_SOURCE", "").strip().lower() == "synthetic":
        warnings.append("market source is synthetic")
    if os.environ.get("BACKTEST_ALLOW_SYNTHETIC", "0").strip().lower() in _TRUE:
        warnings.append("synthetic backtests allowed")
    go_live_env = os.environ.get("GO_LIVE_APPROVED", "0").strip().lower() in _TRUE
    if go_live_env:
        warnings.append("GO_LIVE_APPROVED env is set; host LiveGate still required")
    mode = os.environ.get("TRENDALGO_MODE", "dry-run")
    if mode.strip().lower() == "live":
        warnings.append("TRENDALGO_MODE=live; go-live-gate.sh is still required")
    return {
        "last_trade_age_hours": round(hours, 1) if hours is not None else None,
        "mode": mode,
        "go_live_env_set": go_live_env,
        "warnings": warnings,
    }


def ready_hints(stats: dict[str, Any], stale: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if int(stats.get("trade_count") or 0) < 20:
        hints.append("few dry-run trades")
    if int(stats.get("max_losing_streak") or 0) >= 5:
        hints.append("long losing streak")
    if float(stats.get("max_drawdown_pct") or 0) >= 0.1:
        hints.append("drawdown over 10%")
    hints.extend(list(stale.get("warnings") or []))
    if not hints:
        hints.append("dry-run sample looks populated; run go-live-gate.sh --check-only")
    return hints


def build_golive_report(
    *, trades: list[dict[str, Any]], now: datetime | None = None
) -> dict[str, Any]:
    stats = journal_stats(trades)
    stale = stale_flags(last_trade_at=stats.get("last_trade_at"), now=now or datetime.now(UTC))
    return {
        "advisory": True,
        "bypasses_go_live_gate": False,
        **stats,
        "fee_assumptions": fee_assumptions(),
        "stale": stale,
        "hints": ready_hints(stats, stale),
    }


def report_from_env(data_dir: Path | None = None) -> dict[str, Any]:
    root = data_dir or Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
    return build_golive_report(trades=TradeJournal(root / "journal.db").list_trades(limit=2000))


def emit_golive_readiness(*, data_dir: Path, wait: bool = False) -> dict[str, Any]:
    from trendalgo.notifications.grokbot import emit

    report = report_from_env(data_dir)
    hints = "; ".join(report.get("hints") or [])
    reason = (
        "TrendAlgo go-live readiness (advisory; does not approve live) "
        f"trades={report.get('trade_count', 0)} hints={hints}"
    )
    payload = envelope(event_type="golive_readiness", reason=reason)
    payload["gains"] = report
    return {"report": report, "emit": emit(payload, wait=wait)}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _age_hours(last_trade_at: str | None, now: datetime) -> float | None:
    if not last_trade_at:
        return None
    try:
        ts = datetime.fromisoformat(last_trade_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return (now - ts).total_seconds() / 3600
