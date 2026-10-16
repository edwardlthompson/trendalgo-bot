"""Wizard input checks. Each returns a Problem with a stable reason code, or None when the input passes.

The host is the source of truth for pairing codes (expiry and reuse). These checks catch typing
mistakes before anything is sent, and keep the reason codes stable for the screens and the tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

PERMISSIONS: tuple[str, ...] = (
    "Query Funds",
    "Query Open Orders & Trades",
    "Query Closed Orders & Trades",
    "Modify Orders",
    "Cancel/Close Orders",
)
REQUIRED_PERMISSIONS = frozenset(PERMISSIONS)
PAIRING_CODE_LENGTH = 8
PAIRING_ALPHABET = frozenset("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
MIN_SECRET_LENGTH = 32
LOOPBACK_HOST = "127.0.0.1"


@dataclass(frozen=True)
class Problem:
    code: str
    message: str


def check_key_permissions(ticked: frozenset[str], withdraw_left_off: bool) -> Problem | None:
    """The owner confirms the five trading permissions and that Withdraw Funds is off."""
    if not withdraw_left_off:
        return Problem(
            "kraken.withdraw_unconfirmed",
            "Confirm that Withdraw Funds, Deposit Funds, and Export Data are unticked on Kraken.",
        )
    missing = REQUIRED_PERMISSIONS - ticked
    if missing:
        names = ", ".join(sorted(missing))
        return Problem(
            "kraken.permissions_missing", f"Tick these on Kraken, then confirm: {names}."
        )
    return None


def normalize_pairing_code(text: str) -> str:
    """Dashes and spaces are for reading aloud; the host strips them the same way."""
    return re.sub(r"[\s-]", "", text).upper()


def check_pairing_code(text: str) -> Problem | None:
    code = normalize_pairing_code(text)
    if len(code) != PAIRING_CODE_LENGTH or not set(code) <= PAIRING_ALPHABET:
        return Problem(
            "pair.code_format",
            "A pairing code has 8 letters or digits, with no 0, 1, O, or I. Dashes are fine.",
        )
    return None


def check_owner_secret(secret: str) -> Problem | None:
    if any(char.isspace() for char in secret):
        return Problem("owner.secret_whitespace", "The owner secret has no spaces. Copy it again.")
    if len(secret) < MIN_SECRET_LENGTH:
        return Problem(
            "owner.secret_short",
            f"The owner secret needs at least {MIN_SECRET_LENGTH} characters.",
        )
    return None


def check_loopback_url(url: str) -> Problem | None:
    """Only the practice host on 127.0.0.1 over http. Real hosts need a pinned TLS certificate (W-PORT)."""
    if not _is_loopback_http(url):
        return Problem(
            "host.not_loopback",
            "This build pairs only with the practice host on 127.0.0.1. A real host needs a "
            "pinned TLS certificate, which is not set up yet.",
        )
    return None


def _is_loopback_http(url: str) -> bool:
    """False for text that does not parse as http on 127.0.0.1 with an explicit port."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return parts.scheme == "http" and parts.hostname == LOOPBACK_HOST and port is not None
