"""Read-only key validation probe — balance/query only; never transfer out (Phase 5)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

KeyScope = Literal["query", "trade"]

ALLOWLIST = frozenset({"fetch_balance", "fetchBalance"})


@dataclass(frozen=True)
class KeyVerifyResult:
    ok: bool
    exchange_id: str
    scope: KeyScope
    message: str
    verified_at: str | None = None


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def verify_exchange_keys(
    *,
    exchange_id: str,
    scope: KeyScope,
    fetch_balance: Callable[[], Any],
    method_name: str = "fetch_balance",
) -> KeyVerifyResult:
    """Call only an allowlisted read probe. Never marks trade scope without success."""
    if method_name not in ALLOWLIST:
        return KeyVerifyResult(
            ok=False,
            exchange_id=exchange_id,
            scope=scope,
            message="probe_method_not_allowlisted",
        )
    try:
        balance = fetch_balance()
    except Exception as exc:  # noqa: BLE001 — surface venue errors to UI
        return KeyVerifyResult(
            ok=False,
            exchange_id=exchange_id,
            scope=scope,
            message=f"verify_failed:{type(exc).__name__}",
        )
    if not isinstance(balance, dict):
        return KeyVerifyResult(
            ok=False,
            exchange_id=exchange_id,
            scope=scope,
            message="verify_failed:bad_balance",
        )
    return KeyVerifyResult(
        ok=True,
        exchange_id=exchange_id,
        scope=scope,
        message="keys_ok",
        verified_at=_utc_now(),
    )


def success_dialog_text(result: KeyVerifyResult) -> str:
    scope_label = "read-only (query)" if result.scope == "query" else "trade+query"
    return (
        f"Keys work for {result.exchange_id} ({scope_label}). "
        "No secret values are shown. Live orders still need a separate go-live approval."
    )
