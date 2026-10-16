"""Plan bundle header (ADR-0017). `publisher` and `kid` let another signer be accepted later."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from trendalgo.botd.owner import assert_owner


@dataclass(frozen=True)
class BundleHeader:
    owner_id: str
    publisher: str
    kid: str
    plan_version: int
    bundle_hash: str


def bundle_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def verify_bundle(
    header: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    host_owner_id: str,
    accepted_publishers: frozenset[str] = frozenset({"owner"}),
) -> BundleHeader:
    """Raise ValueError (or ForeignOwnerError) unless the bundle is for this owner and intact."""
    assert_owner(_text(header.get("owner_id")), host_owner_id)
    publisher = _text(header.get("publisher"))
    kid = _text(header.get("kid"))
    if publisher not in accepted_publishers:
        raise ValueError("publisher not accepted")
    if not kid:
        raise ValueError("kid missing")
    plan_version = header.get("plan_version")
    if not isinstance(plan_version, int) or isinstance(plan_version, bool) or plan_version < 1:
        raise ValueError("plan_version must be a positive integer")
    claimed = _text(header.get("bundle_hash"))
    if claimed != bundle_hash(payload):
        raise ValueError("bundle_hash does not match the payload")
    return BundleHeader(
        owner_id=str(header["owner_id"]),
        publisher=publisher,
        kid=kid,
        plan_version=plan_version,
        bundle_hash=claimed,
    )


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""
