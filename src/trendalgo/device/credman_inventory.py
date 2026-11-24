"""Presence-only CredMan inventory — frozen TrendAlgo/* targets (never secrets)."""

from __future__ import annotations

from typing import Any

from trendalgo.device.alpaca_vault import ALPACA_KEY_TARGET, ALPACA_SECRET_TARGET
from trendalgo.device.calendar.vault import CMC_TARGET, COINDAR_TARGET
from trendalgo.device.secrets_vault import TARGET_PREFIX
from trendalgo.device.telegram_vault import TELEGRAM_CHAT_TARGET, TELEGRAM_TOKEN_TARGET
from trendalgo.device.wizard.credentials import (
    OWNER_BEARER_TARGET,
    OWNER_SECRET_TARGET,
    PRACTICE_SECRET_TARGET,
    CredentialError,
    CredentialStore,
    open_store,
)

# AlgoSpecial Forex H1 is public — no CredMan target.
ALGOSPECIAL_NOTE = "AlgoSpecial Forex H1 is keyless (public feed); no CredMan migrate."


def _exchange_targets() -> list[tuple[str, str]]:
    from trendalgo.exchanges.registry import list_exchanges

    out: list[tuple[str, str]] = []
    for entry in list_exchanges():
        eid = entry.id
        base = f"{TARGET_PREFIX}{eid}"
        out.append((f"exchange:{eid}:key", f"{base}/key"))
        out.append((f"exchange:{eid}:secret", f"{base}/secret"))
        out.append((f"exchange:{eid}:meta", f"{base}/meta"))
    return out


def frozen_targets() -> list[tuple[str, str]]:
    """(kind, target) pairs — TargetName strings must never rename without [HUMAN] migrate."""
    fixed = [
        ("telegram:token", TELEGRAM_TOKEN_TARGET),
        ("telegram:chat", TELEGRAM_CHAT_TARGET),
        ("alpaca:key", ALPACA_KEY_TARGET),
        ("alpaca:secret", ALPACA_SECRET_TARGET),
        ("calendar:cmc", CMC_TARGET),
        ("calendar:coindar", COINDAR_TARGET),
        ("owner:secret", OWNER_SECRET_TARGET),
        ("owner:bearer", OWNER_BEARER_TARGET),
        ("owner:practice", PRACTICE_SECRET_TARGET),
    ]
    return fixed + _exchange_targets()


def _present(store: CredentialStore, target: str) -> bool:
    try:
        value = store.read(target)
    except CredentialError:
        return False
    return bool(value and str(value).strip())


def inventory_presence(store: CredentialStore | None = None) -> list[dict[str, Any]]:
    """Return [{kind, target, present}] — never includes secret blobs."""
    try:
        vault = store if store is not None else open_store()
    except CredentialError:
        return [
            {"kind": kind, "target": target, "present": False, "error": "store_unavailable"}
            for kind, target in frozen_targets()
        ]
    rows: list[dict[str, Any]] = []
    for kind, target in frozen_targets():
        rows.append({"kind": kind, "target": target, "present": _present(vault, target)})
    return rows


def inventory_summary(store: CredentialStore | None = None) -> dict[str, Any]:
    rows = inventory_presence(store)
    present_n = sum(1 for r in rows if r.get("present"))
    return {
        "rows": rows,
        "present": present_n,
        "total": len(rows),
        "algospecial": ALGOSPECIAL_NOTE,
        "secrets_exported": False,
    }
