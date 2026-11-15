"""Load config/brokers.registry.json (TradFi lane — not CCXT)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from trendalgo.bundled_config import config_candidates, first_existing

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT = _REPO_ROOT / "config" / "brokers.registry.json"
_REL = "config/brokers.registry.json"


@dataclass(frozen=True)
class BrokerEntry:
    id: str
    brand: str
    lane: str
    asset_classes: tuple[str, ...]
    paper_enabled: bool
    live_enabled: bool
    portfolio_enabled: bool
    scan_enabled: bool
    backtest_enabled: bool
    trading_enabled: bool
    sdk: str
    env_key: str
    env_secret: str
    env_base_url: str
    paper_base_url_default: str
    notes: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "brand": self.brand,
            "lane": self.lane,
            "asset_classes": list(self.asset_classes),
            "paper_enabled": self.paper_enabled,
            "live_enabled": self.live_enabled,
            "portfolio_enabled": self.portfolio_enabled,
            "scan_enabled": self.scan_enabled,
            "backtest_enabled": self.backtest_enabled,
            "trading_enabled": self.trading_enabled,
            "sdk": self.sdk,
        }


@dataclass(frozen=True)
class BrokerRegistry:
    version: int
    default_broker: str
    brokers: tuple[BrokerEntry, ...]

    def by_id(self, broker_id: str) -> BrokerEntry | None:
        for entry in self.brokers:
            if entry.id == broker_id:
                return entry
        return None


def _parse(raw: dict[str, Any]) -> BrokerEntry:
    classes = raw.get("asset_classes") or []
    return BrokerEntry(
        id=str(raw["id"]),
        brand=str(raw.get("brand") or raw["id"]),
        lane=str(raw.get("lane") or "tradfi"),
        asset_classes=tuple(str(c) for c in classes),
        paper_enabled=bool(raw.get("paper_enabled", False)),
        live_enabled=bool(raw.get("live_enabled", False)),
        portfolio_enabled=bool(raw.get("portfolio_enabled", False)),
        scan_enabled=bool(raw.get("scan_enabled", False)),
        backtest_enabled=bool(raw.get("backtest_enabled", False)),
        trading_enabled=bool(raw.get("trading_enabled", False)),
        sdk=str(raw.get("sdk") or ""),
        env_key=str(raw.get("env_key") or ""),
        env_secret=str(raw.get("env_secret") or ""),
        env_base_url=str(raw.get("env_base_url") or ""),
        paper_base_url_default=str(raw.get("paper_base_url_default") or ""),
        notes=str(raw.get("notes") or ""),
    )


@lru_cache(maxsize=1)
def load_broker_registry(path: Path | None = None) -> BrokerRegistry:
    registry_path = path or first_existing(
        config_candidates(_REL, env_var="TRENDALGO_BROKER_REGISTRY", default=_DEFAULT),
        label="broker registry",
    )
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    brokers = tuple(_parse(item) for item in data.get("brokers") or [])
    return BrokerRegistry(
        version=int(data.get("version", 1)),
        default_broker=str(data.get("default_broker") or (brokers[0].id if brokers else "")),
        brokers=brokers,
    )


def list_brokers() -> list[BrokerEntry]:
    return list(load_broker_registry().brokers)


def clear_broker_registry_cache() -> None:
    load_broker_registry.cache_clear()
