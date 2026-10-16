"""Open a signed host client from saved settings and the owner secret vault."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from trendalgo.device.host_client import HostClient
from trendalgo.device.profile import ProfileError, read_json
from trendalgo.device.settings_model import Settings, settings_from_document
from trendalgo.device.wizard.credentials import OWNER_SECRET_TARGET, CredentialStore, open_store


def try_open_host_client(
    settings_path: Path,
    *,
    store: CredentialStore | None = None,
    client_factory: Callable[..., HostClient] = HostClient,
) -> HostClient | None:
    """None when host URL or owner secret is missing. Raises ProfileError on bad settings."""
    try:
        document = read_json(settings_path)
    except ProfileError:
        return None
    settings = settings_from_document(document)
    if settings is None:
        return None
    return open_host_client(settings, store=store, client_factory=client_factory)


def open_host_client(
    settings: Settings,
    *,
    store: CredentialStore | None = None,
    client_factory: Callable[..., HostClient] = HostClient,
) -> HostClient | None:
    host = settings.host_url.strip()
    if not host:
        return None
    vault = store if store is not None else open_store()
    secret = vault.read(OWNER_SECRET_TARGET)
    if not secret:
        return None
    pin = settings.cert_sha256.strip() or None
    return client_factory(host, settings.owner_id, secret, cert_sha256=pin)
