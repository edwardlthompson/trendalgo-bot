"""Persisted state of the streaming LTS port. The host stores it between closed bars (L4, L7)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any

_NUMBER_FIELDS = (
    "position_qty",
    "entry_price",
    "entry_fee",
    "highest_price",
    "cash",
    "reserve_cash",
)


@dataclass
class PortState:
    bars_seen: int = 0
    position_qty: float = 0.0
    entry_price: float = 0.0
    entry_fee: float = 0.0
    highest_price: float = 0.0
    entry_time: str | None = None
    cash: float = 0.0
    reserve_cash: float = 0.0
    previous_buy: bool = False
    exited_on_bar: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PortState:
        """Rebuild state from host storage. Wrong keys or types are refused, never coerced."""
        names = {field.name for field in fields(cls)}
        if set(data) != names:
            raise ValueError(f"state keys must be exactly {sorted(names)}")
        values: dict[str, Any] = {
            "bars_seen": _integer(data["bars_seen"], "bars_seen"),
            "entry_time": _optional_text(data["entry_time"]),
            "previous_buy": _boolean(data["previous_buy"]),
            "exited_on_bar": None
            if data["exited_on_bar"] is None
            else _integer(data["exited_on_bar"], "exited_on_bar"),
        }
        for name in _NUMBER_FIELDS:
            values[name] = _number(data[name], name)
        return cls(**values)


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"state field {name} must be a finite number")
    return float(value)


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"state field {name} must be an integer of at least 0")
    return value


def _optional_text(value: object) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise ValueError("state field entry_time must be text or null")


def _boolean(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError("state field previous_buy must be true or false")
