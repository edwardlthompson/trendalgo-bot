"""Tenant boundary seam (ADR-0017 M5). The host rejects any message for a foreign owner."""

from __future__ import annotations

import hmac


class ForeignOwnerError(ValueError):
    """A message names an owner other than this host's owner, or names none."""


def assert_owner(message_owner_id: str | None, host_owner_id: str) -> None:
    """Fail closed: a missing owner on either side is refused, and the compare is constant-time."""
    if not message_owner_id or not host_owner_id:
        raise ForeignOwnerError("owner_id missing")
    if not hmac.compare_digest(message_owner_id.encode(), host_owner_id.encode()):
        raise ForeignOwnerError("foreign owner_id")
