"""Wizard-facing host calls. Practice mode stays on loopback http only."""

from __future__ import annotations

from collections.abc import Callable

from trendalgo.device.host_client import (
    PAIR_PATH,
    STATUS_PATH,
    UNREACHABLE,
    HostRefusedError,  # re-export for wizard tests
)
from trendalgo.device.host_client import (
    HostClient as SharedHostClient,
)
from trendalgo.device.wizard.credentials import (
    OWNER_SECRET_TARGET,
    CredentialError,
    CredentialStore,
)
from trendalgo.device.wizard.validators import (
    Problem,
    check_owner_secret,
    check_pairing_code,
    normalize_pairing_code,
)
from trendalgo.trading.signed_command import now_seconds

CODE_REFUSED = "The host refused this code. Codes expire after 10 minutes and work once."


class HostClient(SharedHostClient):
    """Practice and pairing: loopback http only."""

    def __init__(
        self,
        base_url: str,
        owner_id: str,
        secret: str,
        *,
        clock: Callable[[], int] = now_seconds,
    ) -> None:
        super().__init__(base_url, owner_id, secret, loopback_only=True, clock=clock)


def pair_host(
    base_url: str,
    owner_id: str,
    owner_secret: str,
    code_text: str,
    store: CredentialStore,
    *,
    clock: Callable[[], int] = now_seconds,
) -> list[Problem]:
    """Check the owner secret, then redeem the pairing code. Success saves the owner secret."""
    typed = [check_owner_secret(owner_secret), check_pairing_code(code_text)]
    problems = [problem for problem in typed if problem is not None]
    if problems:
        return problems
    try:
        client = HostClient(base_url, owner_id, owner_secret, clock=clock)
    except HostRefusedError as exc:
        return [exc.problem]
    status = client.call("GET", STATUS_PATH)
    if status == UNREACHABLE:
        return [Problem("host.unreachable", "The host did not answer. Check the address.")]
    if status != 200:
        return [Problem("owner.refused", "The host refused the owner ID or owner secret.")]
    code = normalize_pairing_code(code_text)
    if client.call("POST", PAIR_PATH, {"code": code}) != 200:
        return [Problem("pair.code_refused", CODE_REFUSED)]
    try:
        store.write(OWNER_SECRET_TARGET, owner_secret)
    except CredentialError as exc:
        return [
            Problem(
                "owner.vault",
                f"The host accepted the code, but the owner secret was not saved. {exc} "
                "Get a new pairing code from the host and pair again.",
            )
        ]
    return []
