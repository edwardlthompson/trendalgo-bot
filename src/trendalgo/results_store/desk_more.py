"""Billing / About / glossary / debug / force-fresh helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_billing_surface() -> dict[str, Any]:
    from trendalgo.device import strings as S

    return {
        "title": S.BILLING_TITLE,
        "subtitle": S.BILLING_SUBTITLE,
        "owner_section": S.BILLING_OWNER_SECTION,
        "owner_body": S.BILLING_OWNER_BODY,
        "settle_label": S.BILLING_SETTLEMENT,
        "settle_help": S.BILLING_SETTLEMENT_HELP,
        "settle_enabled": False,
        "referrals_help": S.BILLING_REFERRALS_HELP,
        "tier": "owner-only",
    }


def load_about_surface() -> dict[str, Any]:
    from trendalgo import __version__
    from trendalgo.device import strings as S
    from trendalgo.device.about.github_release import changelog_url
    from trendalgo.device.github_feedback.release_repo import load_release_repo

    repo = load_release_repo() or "edwardbbaity/trendalgo-bot"
    return {
        "version": __version__,
        "version_line": S.ABOUT_VERSION.format(version=__version__),
        "body": S.ABOUT_BODY,
        "donate": S.ABOUT_DONATE,
        "changelog_url": changelog_url(repo),
        "support": S.ABOUT_SUPPORT,
    }


def load_glossary_surface(*, query: str = "") -> dict[str, Any]:
    from trendalgo.device import strings as S
    from trendalgo.device.glossary_model import (
        filter_entries,
        find_glossary_entry,
        load_glossary,
    )

    entries, err = load_glossary()
    shown = filter_entries(entries, query)
    rows = [
        {
            "id": e.id,
            "title": e.title,
            "category": e.category,
            "short": e.short,
            "long": e.long,
            "formula": e.formula,
        }
        for e in shown[:200]
    ]
    hit = find_glossary_entry(entries, query) if query.strip() else None
    entry: dict[str, Any] | None = None
    if hit is not None:
        pool = _pool_label_for(hit.id)
        entry = {
            "id": hit.id,
            "title": hit.title,
            "category": hit.category,
            "pool": pool,
            "subtitle": f"{hit.category} · {pool}",
            "short": hit.short,
            "long": hit.long,
            "formula": hit.formula,
            "formula_label": S.GLOSSARY_DETAIL_FORMULA,
            "related": list(hit.related),
        }
    return {
        "query": query,
        "rows": rows,
        "shown": len(shown),
        "total": len(entries),
        "error": err,
        "entry": entry,
        "miss_title": S.SCANNER_GLOSSARY_MISS_TITLE,
        "miss_body": S.SCANNER_GLOSSARY_MISS_BODY.format(name=query or "—"),
        "found": entry is not None,
    }


def load_debug_surface(root: Path) -> dict[str, Any]:
    log_path = root / "device.log"
    lines: list[str] = []
    if log_path.is_file():
        text = log_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()[-200:]
    return {
        "path": str(log_path),
        "exists": log_path.is_file(),
        "lines": lines,
        "count": len(lines),
    }


def apply_force_fresh(root: Path) -> list[str]:
    from trendalgo.device.debug_scan import clear_scan_caches

    return clear_scan_caches(root)


def load_notify_surface(root: Path) -> dict[str, Any]:
    from dataclasses import asdict

    from trendalgo.device import strings as S
    from trendalgo.device.alert_preview import (
        KINDS,
        kind_master_on,
        sample_event,
        telegram_preview,
        windows_preview,
    )
    from trendalgo.device.notify_prefs import load_prefs

    prefs = load_prefs(root)
    kinds = [
        {
            "id": "logs",
            "label": S.NOTIFY_KIND_LOGS,
            "windows": prefs.windows_logs,
            "telegram": prefs.telegram_logs,
        },
        {
            "id": "entered",
            "label": S.NOTIFY_KIND_ENTERED,
            "windows": prefs.windows_entered,
            "telegram": prefs.telegram_entered,
        },
        {
            "id": "left",
            "label": S.NOTIFY_KIND_LEFT,
            "windows": prefs.windows_left,
            "telegram": prefs.telegram_left,
        },
        {
            "id": "trades",
            "label": S.NOTIFY_KIND_TRADES,
            "windows": prefs.windows_trades,
            "telegram": prefs.telegram_trades,
        },
    ]
    ribbon = []
    for kind in KINDS:
        on = kind_master_on(prefs, kind)
        event = sample_event(kind)
        win_title, win_body = windows_preview(event)
        ribbon.append(
            {
                "id": kind,
                "label": {
                    "entered": S.ALERTS_TAB_ENTERED,
                    "left": S.ALERTS_TAB_LEFT,
                    "trades": S.ALERTS_TAB_TRADES,
                }[kind],
                "on": on,
                "state": S.ALERTS_NOTIFY_ON if on else S.ALERTS_NOTIFY_OFF,
                "windows_title": win_title,
                "windows_body": win_body,
                "telegram_body": telegram_preview(event),
            }
        )
    return {
        "section": S.NOTIFY_SECTION,
        "help": S.NOTIFY_SECTION_HELP,
        "ribbon_help": S.ALERTS_RIBBON_HELP,
        "col_windows": S.NOTIFY_COL_WINDOWS,
        "col_telegram": S.NOTIFY_COL_TELEGRAM,
        "telegram_enabled": prefs.telegram_enabled,
        "start_with_windows": prefs.start_with_windows,
        "grokbot_help": S.NOTIFY_GROKBOT_HELP,
        "kinds": kinds,
        "ribbon": ribbon,
        "prefs": asdict(prefs),
    }


def load_credman_surface() -> dict[str, Any]:
    """Presence-only vault inventory for Avalonia Settings → Keys (AV-P1b)."""
    from trendalgo.device.credman_inventory import inventory_summary

    return inventory_summary()


def _pool_label_for(indicator_id: str) -> str:
    if str(indicator_id or "").casefold() in {"oracle-max", "oracle max"}:
        return "Baseline"
    try:
        from trendalgo.ta.strategy_pool import pool_label

        return pool_label(indicator_id)
    except Exception:
        return "TA"
