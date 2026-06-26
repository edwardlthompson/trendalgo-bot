"""DEX dry-run swap runner — simulation only, no broadcast (S23, CM-10)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DexDryRunRunner:
    """Simulate DEX swaps via registry plugins — never broadcasts transactions."""

    app_dry_run: bool = True
    _history: list[dict[str, Any]] = field(default_factory=list)

    def preview(
        self,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
    ) -> dict[str, Any]:
        from trendalgo.dex.router import preview_dex_swap

        return preview_dex_swap(chain, sell_token, buy_token, sell_amount)

    def execute(
        self,
        chain: str,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
    ) -> dict[str, Any]:
        from trendalgo.dex.router import dry_run_dex_swap

        result = dry_run_dex_swap(
            chain,
            sell_token,
            buy_token,
            sell_amount,
            app_dry_run=self.app_dry_run,
            live_swap=False,
        )
        self._history.append(result)
        return result

    @property
    def history(self) -> list[dict[str, Any]]:
        return list(self._history)
