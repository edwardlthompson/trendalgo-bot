"""Fetch + merge calendar events into the local cache."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trendalgo.device.calendar import cache, vault
from trendalgo.device.calendar.model import CalendarEvent, merge_events
from trendalgo.device.calendar.providers import coindar, coinmarketcal
from trendalgo.device.calendar.providers.coinmarketcal import ProviderError
from trendalgo.device.wizard.credentials import CredentialStore


def refresh_cache(root: Path, store: CredentialStore | None = None) -> list[CalendarEvent]:
    batches: list[list[CalendarEvent]] = []
    cmc = vault.read_cmc_key(store)
    if cmc:
        try:
            batches.append(coinmarketcal.fetch_events(cmc))
        except ProviderError:
            pass
    token = vault.read_coindar_token(store)
    if token:
        try:
            batches.append(coindar.fetch_events(token))
        except ProviderError:
            pass
    events = merge_events(batches)
    if events:
        cache.save_events(root, events, fetched_at=datetime.now(tz=UTC).isoformat())
    return events
