"""Exchange registry — loads config/exchanges.registry.json."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_REGISTRY = _REPO_ROOT / "config" / "exchanges.registry.json"


def _registry_path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    env = os.environ.get("TRENDALGO_EXCHANGE_REGISTRY")
    if env:
        return Path(env)
    for candidate in (_DEFAULT_REGISTRY, Path.cwd() / "config" / "exchanges.registry.json"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"exchange registry not found (tried {_DEFAULT_REGISTRY} and cwd/config)"
    )


@dataclass(frozen=True)
class ExchangeEntry:
    id: str
    brand: str
    tier: str
    portfolio_enabled: bool
    trading_enabled: bool
    ccxt_id: str
    env_key: str
    env_secret: str
    us_retail: bool = False
    us_restricted: bool = False
    quote_currency: str = "USD"
    usd_aliases: tuple[str, ...] = ("USD", "ZUSD", "USDT")
    sync_interval_sec: int | None = None

    def has_api_keys(self) -> bool:
        return bool(os.environ.get(self.env_key) and os.environ.get(self.env_secret))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "brand": self.brand,
            "tier": self.tier,
            "portfolio_enabled": self.portfolio_enabled,
            "trading_enabled": self.trading_enabled,
            "ccxt_id": self.ccxt_id,
            "us_retail": self.us_retail,
            "us_restricted": self.us_restricted,
            "quote_currency": self.quote_currency,
            "configured": self.has_api_keys(),
        }


@dataclass(frozen=True)
class ExchangeRegistry:
    version: int
    exchanges: tuple[ExchangeEntry, ...]
    default_sync_interval_sec: int = 15
    worldwide_trading_phase: int = 0

    def by_id(self, exchange_id: str) -> ExchangeEntry | None:
        for entry in self.exchanges:
            if entry.id == exchange_id:
                return entry
        return None


def _parse_entry(raw: dict[str, Any]) -> ExchangeEntry:
    aliases = raw.get("usd_aliases", ["USD", "ZUSD", "USDT"])
    return ExchangeEntry(
        id=str(raw["id"]),
        brand=str(raw["brand"]),
        tier=str(raw["tier"]),
        portfolio_enabled=bool(raw.get("portfolio_enabled", False)),
        trading_enabled=bool(raw.get("trading_enabled", False)),
        ccxt_id=str(raw.get("ccxt_id", raw["id"])),
        env_key=str(raw["env_key"]),
        env_secret=str(raw["env_secret"]),
        us_retail=bool(raw.get("us_retail", False)),
        us_restricted=bool(raw.get("us_restricted", False)),
        quote_currency=str(raw.get("quote_currency", "USD")),
        usd_aliases=tuple(str(a) for a in aliases),
        sync_interval_sec=int(raw["sync_interval_sec"]) if raw.get("sync_interval_sec") else None,
    )


@lru_cache(maxsize=1)
def load_registry(path: Path | None = None) -> ExchangeRegistry:
    registry_path = _registry_path(path)
    if not registry_path.is_file():
        raise FileNotFoundError(f"exchange registry not found: {registry_path}")
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    entries = tuple(_parse_entry(item) for item in data.get("exchanges", []))
    return ExchangeRegistry(
        version=int(data.get("version", 1)),
        exchanges=entries,
        default_sync_interval_sec=int(data.get("default_sync_interval_sec", 15)),
        worldwide_trading_phase=int(data.get("worldwide_trading_phase", 0)),
    )


def list_exchanges() -> list[ExchangeEntry]:
    return list(load_registry().exchanges)


def list_portfolio_exchanges() -> list[ExchangeEntry]:
    return [e for e in list_exchanges() if e.portfolio_enabled]


def list_trading_exchanges() -> list[ExchangeEntry]:
    return [e for e in list_exchanges() if e.trading_enabled]


def list_worldwide_trading_exchanges() -> list[ExchangeEntry]:
    return [e for e in list_trading_exchanges() if e.us_restricted or not e.us_retail]


def get_entry(exchange_id: str) -> ExchangeEntry:
    entry = load_registry().by_id(exchange_id)
    if entry is None:
        raise KeyError(f"unknown exchange: {exchange_id}")
    return entry
