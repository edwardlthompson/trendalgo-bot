"""Icon registry package."""

from trendalgo.icons.store import IconStore
from trendalgo.icons.sync import sync_all, sync_coins, sync_exchanges

__all__ = ["IconStore", "sync_all", "sync_coins", "sync_exchanges"]
