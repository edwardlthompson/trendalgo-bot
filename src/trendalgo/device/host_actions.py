"""Pure helpers for host send/sync (tested without Qt)."""

from __future__ import annotations

from typing import Any

from trendalgo.device.host_client import UNREACHABLE, HostClient, HostRefusedError, HostResponse


def send_plan_bundle(client: HostClient, bundle: dict[str, Any]) -> tuple[bool, str]:
    """Return (ok, user-facing status line)."""
    try:
        response = client.put_plan(bundle)
    except HostRefusedError as exc:
        return False, exc.problem.code
    if response.status == UNREACHABLE:
        return False, "host_unreachable"
    if response.ok:
        version = int((response.data or {}).get("plan_version", 0))
        digest = str((response.data or {}).get("bundle_hash", ""))[:12]
        return True, f"sent:{version}:{digest}"
    if response.status == 409:
        return False, "plan_stale"
    if response.status in (403, 422):
        return False, "plan_refused"
    return False, f"plan_http_{response.status}"


def portfolio_status_message(status: HostResponse) -> tuple[bool, str]:
    """True when the host returned a portfolio payload; otherwise an honest empty reason."""
    if status.status == UNREACHABLE:
        return False, "host_unreachable"
    if not status.ok:
        return False, "host_refused"
    data = status.data or {}
    portfolio = data.get("portfolio")
    if isinstance(portfolio, dict) and portfolio:
        return True, "has_portfolio"
    return False, "no_portfolio_payload"


def host_health_linked(status: HostResponse) -> bool:
    return status.ok


def post_bot_command(client: HostClient, action: str, bot_id: str, key: str) -> HostResponse:
    return client.post_command(action, bot_id, key)
