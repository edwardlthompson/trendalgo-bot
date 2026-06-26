"""DEX signer — env-only on VPS (CM-9, S24)."""

from __future__ import annotations

import hashlib
import hmac
import os


def _signer_key() -> str | None:
    key = os.environ.get("DEX_SIGNER_KEY", "").strip()
    return key or None


def signer_configured() -> bool:
    return _signer_key() is not None


def signer_fingerprint() -> str | None:
    """Public fingerprint for audit logs — never the raw key."""
    key = _signer_key()
    if not key:
        return None
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def sign_swap_payload(payload: str) -> str:
    """HMAC-sign swap payload; raises if signer missing."""
    key = _signer_key()
    if not key:
        raise ValueError("DEX_SIGNER_KEY required on VPS for live swaps")
    digest = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"0x{digest}"
