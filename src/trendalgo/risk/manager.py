"""Position sizing, daily loss cap, and circuit breaker (R1 to R3)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

from trendalgo.risk.config import RiskLimits

logger = logging.getLogger(__name__)


class StakeRejected(ValueError):
    """A zero, negative, or non-finite stake. No order may be placed for it (R3)."""


def utc_day_start(now: datetime) -> datetime:
    """Midnight UTC at the start of the day that now falls in (R2)."""
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class RiskState:
    daily_pnl_usd: float = 0.0
    peak_equity_usd: float = 0.0
    circuit_breaker_active: bool = False
    paused: bool = False
    day_key: str = ""


@dataclass
class RiskManager:
    limits: RiskLimits
    wallet_usd: float
    state: RiskState = field(default_factory=RiskState)

    def __post_init__(self) -> None:
        if self.state.peak_equity_usd <= 0:
            self.state.peak_equity_usd = self.wallet_usd

    def set_equity(self, balance_usd: float, open_position_usd: float = 0.0) -> float:
        """Host equity is the exchange balance plus the open position value (R3)."""
        if not (math.isfinite(balance_usd) and math.isfinite(open_position_usd)):
            raise ValueError("equity inputs must be finite numbers")
        self.wallet_usd = max(0.0, balance_usd + open_position_usd)
        return self.wallet_usd

    def compute_stake(self, proposed_usd: float) -> float:
        if not math.isfinite(proposed_usd) or proposed_usd <= 0:
            raise StakeRejected(f"stake must be a positive number, got {proposed_usd}")
        pct_cap = self.wallet_usd * self.limits.max_stake_pct
        cap = min(self.limits.max_stake_usd, pct_cap)
        return round(max(0.0, min(proposed_usd, cap)), 2)

    def record_pnl(self, delta_usd: float) -> None:
        self.state.daily_pnl_usd += delta_usd
        self._refresh_peak_and_breaker()

    def sync_daily_pnl(self, realized_pnl_usd: float, now: datetime) -> None:
        """Set today's realized PnL from the journal's fills. The day moves at UTC midnight (R2)."""
        self.state.day_key = now.astimezone(UTC).date().isoformat()
        self.state.daily_pnl_usd = realized_pnl_usd
        self._refresh_peak_and_breaker()

    def _refresh_peak_and_breaker(self) -> None:
        equity = self.wallet_usd + self.state.daily_pnl_usd
        if equity > self.state.peak_equity_usd:
            self.state.peak_equity_usd = equity
        self._refresh_circuit_breaker(equity)

    def _refresh_circuit_breaker(self, equity: float) -> None:
        if self.state.peak_equity_usd <= 0:
            return
        drawdown = (self.state.peak_equity_usd - equity) / self.state.peak_equity_usd
        if drawdown >= self.limits.circuit_breaker_drawdown_pct:
            self.state.circuit_breaker_active = True

    def is_daily_loss_exceeded(self) -> bool:
        return self.state.daily_pnl_usd <= -self.limits.daily_loss_cap_usd

    def can_open_trade(self) -> tuple[bool, str]:
        if self.state.paused:
            return False, "trading paused"
        if self.state.circuit_breaker_active:
            return False, "circuit breaker active"
        if self.is_daily_loss_exceeded():
            return False, "daily loss cap exceeded"
        return True, "ok"

    def pause(self) -> None:
        self.state.paused = True

    def resume(self) -> None:
        """Un-pause new entries. The circuit breaker is not touched (R1); see reset_breaker."""
        self.state.paused = False

    def reset_breaker(self, *, confirm: bool, operator: str) -> None:
        """Clear a tripped breaker. A separate command: it needs confirm=True and a named operator."""
        if not confirm:
            raise ValueError("reset_breaker needs confirm=True")
        if not operator.strip():
            raise ValueError("reset_breaker needs the operator's name")
        was_active = self.state.circuit_breaker_active
        self.state.circuit_breaker_active = False
        # Drawdown is measured from the reset point, so the breaker does not re-trip on old peaks.
        self.state.peak_equity_usd = self.wallet_usd + self.state.daily_pnl_usd
        logger.warning("circuit breaker reset by %s (was active: %s)", operator, was_active)

    def reset_daily(self) -> None:
        self.state.daily_pnl_usd = 0.0
