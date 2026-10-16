"""Provider circuit stub — always closed (allow)."""

from __future__ import annotations

from typing import Any


class ProviderCallCircuit:
    def allow(self) -> bool:
        return True

    def record_success(self) -> None:
        return None

    def record_failure(self) -> None:
        return None


def circuit_from_settings(_settings: Any, _name: str) -> ProviderCallCircuit | None:
    return ProviderCallCircuit()
