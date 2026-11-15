"""Weekly digest: Telegram compact text + optional Grok Bot webhook. Off by default."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.notifications.grokbot_payload import envelope
from trendalgo.risk.journal import TradeJournal

_TRUE = frozenset({"1", "true", "yes", "on"})


def weekly_enabled() -> bool:
    return os.environ.get("WEEKLY_DIGEST_ENABLED", "0").strip().lower() in _TRUE


def weekly_dow() -> str:
    raw = os.environ.get("WEEKLY_DIGEST_DOW", "sun").strip().lower() or "sun"
    return raw[:3]


def weekly_hour() -> int:
    try:
        return max(0, min(23, int(os.environ.get("WEEKLY_DIGEST_HOUR", "0"))))
    except ValueError:
        return 0


def build_weekly_digest(
    *,
    trades: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    history: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    stamp = now or datetime.now(UTC)
    since = (stamp - timedelta(days=7)).replace(microsecond=0).isoformat()
    week = [row for row in trades if str(row.get("created_at") or "") >= since]
    sells = [row for row in week if str(row.get("side") or "").lower() in {"sell", "short"}]
    pnl_by: dict[str, float] = {}
    for row in sells:
        key = str(row.get("signal_source") or "unknown")
        pnl_by[key] = pnl_by.get(key, 0.0) + float(row.get("pnl_usd") or 0)
    week_alerts = [row for row in alerts if str(row.get("created_at") or "") >= since]
    tiers = Counter(str(row.get("tier") or "?").upper() for row in week_alerts)
    recur = Counter(str(row.get("pair") or "") for row in week_alerts)
    events = history or []
    entered = [
        str(row.get("pair") or row.get("symbol") or "")
        for row in events
        if str(row.get("kind") or "") == "qualified_enter"
        and str(row.get("at") or row.get("created_at") or "") >= since
    ]
    left = [
        str(row.get("pair") or row.get("symbol") or "")
        for row in events
        if str(row.get("kind") or "") in {"qualified_leave", "watchlist_leave"}
        and str(row.get("at") or row.get("created_at") or "") >= since
    ]
    top_strategy = ""
    top_pnl = 0.0
    if pnl_by:
        top_strategy, top_pnl = max(pnl_by.items(), key=lambda item: item[1])
    return {
        "since_utc": since,
        "entered": [p for p in entered if p][:12],
        "left": [p for p in left if p][:12],
        "tier_counts": dict(tiers),
        "trade_count": len(week),
        "pnl_usd": round(sum(float(row.get("pnl_usd") or 0) for row in sells), 4),
        "pnl_by_strategy": {k: round(v, 4) for k, v in pnl_by.items()},
        "top_strategy": top_strategy or None,
        "top_strategy_pnl": round(top_pnl, 4) if top_strategy else None,
        "recurring_pairs": [p for p, _n in recur.most_common(8) if p],
    }


def format_weekly_telegram(digest: dict[str, Any]) -> str:
    entered = ", ".join(digest.get("entered") or []) or "—"
    left = ", ".join(digest.get("left") or []) or "—"
    tiers = digest.get("tier_counts") or {}
    tier_txt = " ".join(f"{k}:{tiers[k]}" for k in sorted(tiers)) or "none"
    recur = ", ".join(digest.get("recurring_pairs") or []) or "—"
    strat = digest.get("top_strategy") or "—"
    return (
        "TrendAlgo weekly\n"
        f"Entered: {entered}\n"
        f"Left: {left}\n"
        f"Tiers {tier_txt}\n"
        f"Trades: {digest.get('trade_count', 0)}  "
        f"PnL: ${float(digest.get('pnl_usd') or 0):+.2f}\n"
        f"Top strategy: {strat} ${float(digest.get('top_strategy_pnl') or 0):+.2f}\n"
        f"Recurring: {recur}"
    )


def run_scheduled(*, on_log: Any | None = None) -> None:
    if not weekly_enabled():
        return
    data = Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
    from trendalgo.scanner.store import ScannerStore

    try:
        emit_weekly_digest(
            data_dir=data,
            scanner_store=ScannerStore(data / "scanner.db"),
            journal=TradeJournal(data / "journal.db"),
        )
    except Exception as exc:  # noqa: BLE001
        if on_log:
            on_log(f"weekly digest failed: {exc}")


def load_alert_history(data_dir: Path) -> list[dict[str, Any]]:
    device = Path(os.environ.get("TRENDALGO_DEVICE_DIR") or Path.home() / ".trendalgo" / "device")
    rows: list[dict[str, Any]] = []
    for root in (data_dir, device):
        path = root / "scanner_alerts.json"
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        chunk = raw.get("alerts") if isinstance(raw, dict) else raw
        if isinstance(chunk, list):
            rows.extend(row for row in chunk if isinstance(row, dict))
    return rows


def emit_weekly_digest(*, data_dir: Path, scanner_store: Any, journal: TradeJournal) -> str:
    from trendalgo.notifications.grokbot import emit, telegram_ai_note
    from trendalgo.notifications.telegram import TelegramCommands

    alerts = scanner_store.list_alerts(limit=2500) if hasattr(scanner_store, "list_alerts") else []
    digest = build_weekly_digest(
        trades=journal.list_trades(limit=2000), alerts=alerts, history=load_alert_history(data_dir)
    )
    text = telegram_ai_note(format_weekly_telegram(digest))
    TelegramCommands().send_message(text)
    payload = envelope(event_type="weekly_digest", reason=text)
    payload["gains"] = digest
    emit(payload)
    return text
