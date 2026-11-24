"""Bots hub ops surfaces — performance, journal, local panic (AV-P1f)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import BOTS_DB, JOURNAL_DB


def load_bots_performance_surface(root: Path) -> dict[str, Any]:
    from trendalgo.device.bots_performance import performance_rows

    rows = performance_rows(root / BOTS_DB, root / JOURNAL_DB)
    return {
        "rows": [
            {
                "label": r.display_label,
                "pair": r.pair,
                "strategy": r.strategy,
                "trades": r.trade_count,
                "win_rate": None if r.win_rate is None else round(r.win_rate * 100.0, 2),
                "pnl": round(r.realized_pnl, 2),
                "retired": r.retired,
            }
            for r in rows
        ],
        "count": len(rows),
    }


def load_bots_journal_surface(root: Path, *, limit: int = 200) -> dict[str, Any]:
    path = root / JOURNAL_DB
    if not path.is_file():
        return {"rows": [], "count": 0, "empty": True}
    from trendalgo.risk.journal import TradeJournal

    trades = TradeJournal(path).list_trades(limit=limit)
    rows: list[dict[str, Any]] = []
    for t in trades:
        if not isinstance(t, dict):
            continue
        rows.append(
            {
                "at": str(t.get("created_at") or t.get("fill_ts") or ""),
                "bot_id": t.get("bot_id"),
                "pair": str(t.get("pair") or ""),
                "side": str(t.get("side") or ""),
                "pnl": t.get("pnl_usd"),
            }
        )
    return {"rows": rows, "count": len(rows), "empty": len(rows) == 0}


def run_bots_panic(root: Path) -> dict[str, Any]:
    """Local panic + host flatten when linked (AV-G-BOT2 / StatusPage parity)."""
    import secrets

    from trendalgo.bots.orchestrator import BotOrchestrator
    from trendalgo.device.host_actions import post_bot_command
    from trendalgo.device.host_session import try_open_host_client
    from trendalgo.device.profile import SETTINGS_FILE
    from trendalgo.trading.order_journal import OrderJournal
    from trendalgo.trading.panic import run_panic

    bots_path = root / BOTS_DB
    journal_path = root / JOURNAL_DB
    if not bots_path.is_file():
        return {"ok": False, "error": "no_bots_db", "paused": 0}
    orch = BotOrchestrator(bots_path)
    journal = OrderJournal(journal_path) if journal_path.is_file() else OrderJournal(bots_path)
    flatten_calls: list[dict[str, str]] = []
    host_linked = False
    settings_path = root / SETTINGS_FILE

    def _flatten(action: str, bot_id: str) -> None:
        nonlocal host_linked
        client = try_open_host_client(settings_path)
        if client is None:
            return
        host_linked = True
        post_bot_command(client, action, bot_id, secrets.token_urlsafe(12))
        flatten_calls.append({"action": str(action), "bot_id": str(bot_id)})

    result = run_panic(
        guard=journal, orchestrator=orch, post_flatten=_flatten, reason="shell_panic"
    )
    return {
        "ok": True,
        "paused": len(result.paused_bots),
        "halted": list(result.halted_exchanges),
        "paused_bots": list(result.paused_bots),
        "flatten_requested": list(result.flatten_requested),
        "host_linked": host_linked,
        "host_flatten_calls": len(flatten_calls),
        "flatten_calls": flatten_calls,
    }


def load_live_bot_cards(root: Path) -> list[dict[str, Any]]:
    """Local bots.db cards for start/stop (AV-G-BOT3)."""
    bots_path = root / BOTS_DB
    if not bots_path.is_file():
        return []
    try:
        from trendalgo.bots.orchestrator import BotOrchestrator

        orch = BotOrchestrator(bots_path)
        out: list[dict[str, Any]] = []
        for bot in orch.list_bots():
            out.append(
                {
                    "id": str(bot.get("id") or ""),
                    "name": str(bot.get("label") or bot.get("name") or ""),
                    "pair": str(bot.get("pair") or ""),
                    "strategy": str(bot.get("strategy_id") or bot.get("strategy") or ""),
                    "enabled": bool(bot.get("enabled")),
                    "state": "running" if bot.get("enabled") else "paused",
                    "source": "bots.db",
                }
            )
        return out
    except Exception:
        return []


def set_bot_enabled(root: Path, bot_id: str, *, enabled: bool) -> dict[str, Any]:
    bots_path = root / BOTS_DB
    if not bots_path.is_file():
        return {"ok": False, "error": "no_bots_db"}
    try:
        bid = int(str(bot_id).strip())
    except (TypeError, ValueError):
        return {"ok": False, "error": "bad_bot_id"}
    try:
        from trendalgo.bots.orchestrator import BotOrchestrator

        orch = BotOrchestrator(bots_path)
        if orch.get_bot(bid) is None:
            return {"ok": False, "error": "missing_bot"}
        orch.set_enabled(bid, enabled)
        return {"ok": True, "bot_id": bid, "enabled": enabled}
    except Exception as exc:
        return {"ok": False, "error": "set_enabled_failed", "detail": str(exc)}


def publish_plan_to_host(root: Path) -> dict[str, Any]:
    """Build plan bundle from plan.json and PUT to linked botd (AV-G-BOT1)."""
    from trendalgo.device.host_actions import send_plan_bundle
    from trendalgo.device.host_session import try_open_host_client
    from trendalgo.device.plan_model import (
        build_bundle,
        check_plan,
        load_plan,
        next_plan_version,
        plan_document,
    )
    from trendalgo.device.profile import (
        PLAN_FILE,
        SETTINGS_FILE,
        ProfileError,
        read_json,
        write_json,
    )
    from trendalgo.device.settings_model import settings_from_document

    plan_path = root / PLAN_FILE
    settings_path = root / SETTINGS_FILE
    try:
        raw = read_json(plan_path) if plan_path.is_file() else {}
    except ProfileError as exc:
        return {"ok": False, "error": "plan_unreadable", "detail": str(exc)}
    try:
        version, bots = load_plan(raw) if isinstance(raw, dict) and raw else (0, [])
    except Exception as exc:
        return {"ok": False, "error": "plan_invalid", "detail": str(exc)}
    problems = check_plan(bots)
    if problems:
        return {"ok": False, "error": "plan_check", "detail": " ".join(problems)}
    settings = settings_from_document(read_json(settings_path)) if settings_path.is_file() else None
    owner = settings.owner_id if settings is not None else None
    if not owner:
        return {"ok": False, "error": "needs_owner"}
    client = try_open_host_client(settings_path)
    if client is None:
        return {"ok": False, "error": "no_host"}
    if not version:
        version = next_plan_version(0)
        try:
            write_json(plan_path, plan_document(version, bots))
        except OSError as exc:
            return {"ok": False, "error": "plan_write", "detail": str(exc)}
    bundle = build_bundle(bots, owner_id=owner, plan_version=version)
    ok, code = send_plan_bundle(client, bundle)
    if not ok:
        return {"ok": False, "error": code, "bots": len(bots), "version": version}
    digest = code.split(":")[-1] if code.startswith("sent:") else ""
    sent_version = int(code.split(":")[1]) if code.startswith("sent:") else version
    return {
        "ok": True,
        "code": code,
        "version": sent_version,
        "digest": digest,
        "bots": len(bots),
    }
