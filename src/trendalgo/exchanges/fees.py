"""Exchange fee schedules for backtest P&L (retail-default taker/maker)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from trendalgo.exchanges.fee_store import get_fee_store


@dataclass(frozen=True)
class ExchangeFeeSchedule:
    exchange_id: str
    taker_pct: float
    maker_pct: float
    tier: str
    source_url: str
    source: str = "seed"
    fetched_at: str | None = None
    updated_at: str | None = None

    def round_trip_taker_cost(self, stake_usd: float) -> float:
        """Entry + exit taker fee on notional."""
        return 2.0 * self.taker_pct * stake_usd

    def to_dict(self) -> dict[str, Any]:
        return {
            "exchange_id": self.exchange_id,
            "taker_pct": self.taker_pct,
            "maker_pct": self.maker_pct,
            "tier": self.tier,
            "source_url": self.source_url,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "updated_at": self.updated_at,
        }


def clear_fee_cache() -> None:
    _row_to_schedule.cache_clear()


@lru_cache(maxsize=64)
def _row_to_schedule(exchange_id: str) -> ExchangeFeeSchedule:
    row = get_fee_store().get(exchange_id.lower())
    if row is None:
        raise KeyError(f"no fee schedule for exchange: {exchange_id}")
    return ExchangeFeeSchedule(
        exchange_id=str(row["exchange_id"]),
        taker_pct=float(row["taker_pct"]),
        maker_pct=float(row["maker_pct"]),
        tier=str(row["tier"]),
        source_url=str(row.get("source_url") or ""),
        source=str(row.get("source") or "seed"),
        fetched_at=row.get("fetched_at"),
        updated_at=row.get("updated_at"),
    )


def get_fee_schedule(exchange_id: str) -> ExchangeFeeSchedule:
    return _row_to_schedule(exchange_id.lower())


def all_fee_schedules() -> list[ExchangeFeeSchedule]:
    rows = get_fee_store().list_all()
    return [_row_to_schedule(str(r["exchange_id"])) for r in rows]


def round_trip_taker_cost(stake_usd: float, taker_pct: float) -> float:
    return 2.0 * taker_pct * stake_usd
