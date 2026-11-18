"""Position sizing, daily loss cap, and circuit breaker (R1 to R3; RISK-02..05)."""

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
    # After a manual breaker reset, wait for recovery under the DD threshold before re-arming.
    breaker_needs_recovery: bool = False


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
        self._refresh_peak_and_breaker()
        return self.wallet_usd

    def compute_stake(self, proposed_usd: float) -> float:
        if not math.isfinite(proposed_usd) or proposed_usd <= 0:
            raise StakeRejected(f"stake must be a positive number, got {proposed_usd}")
        pct_cap = self.wallet_usd * self.limits.max_stake_pct
        cap = min(self.limits.max_stake_usd, pct_cap)
        stake = round(max(0.0, min(proposed_usd, cap)), 2)
        if stake <= 0:
            raise StakeRejected(f"stake rounds to {stake}; minimum viable stake is 0.01 after caps")
        return stake

    def record_pnl(self, delta_usd: float) -> None:
        self.state.daily_pnl_usd += delta_usd
        self._refresh_peak_and_breaker()

    def sync_daily_pnl(self, realized_pnl_usd: float, now: datetime) -> None:
        """Set today's realized PnL from the journal's fills. The day moves at UTC midnight (R2)."""
        self.state.day_key = now.astimezone(UTC).date().isoformat()
        self.state.daily_pnl_usd = realized_pnl_usd
        self._refresh_peak_and_breaker()

    def _refresh_peak_and_breaker(self) -> None:
        # RISK-02: wallet already is balance+open; never add daily_pnl on top.
        equity = self.wallet_usd
        if equity > self.state.peak_equity_usd:
            self.state.peak_equity_usd = equity
        self._refresh_circuit_breaker(equity)

    def _refresh_circuit_breaker(self, equity: float) -> None:
        if self.state.peak_equity_usd <= 0:
            return
        drawdown = (self.state.peak_equity_usd - equity) / self.state.peak_equity_usd
        threshold = self.limits.circuit_breaker_drawdown_pct
        if self.state.breaker_needs_recovery:
            if drawdown < threshold:
                self.state.breaker_needs_recovery = False
            return
        if drawdown >= threshold:
            self.state.circuit_breaker_active = True

    def is_daily_loss_exceeded(self) -> bool:
        return self.state.daily_pnl_usd <= -self.limits.daily_loss_cap_usd

    def _roll_day_if_needed(self, now: datetime) -> None:
        today = now.astimezone(UTC).date().isoformat()
        if self.state.day_key and self.state.day_key != today:
            self.state.daily_pnl_usd = 0.0
            self.state.day_key = today
        elif not self.state.day_key:
            self.state.day_key = today

    def can_open_trade(self, now: datetime | None = None) -> tuple[bool, str]:
        self._roll_day_if_needed(now or datetime.now(UTC))
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
        """Clear a tripped breaker. Peak high-water mark is kept (RISK-04)."""
        if not confirm:
            raise ValueError("reset_breaker needs confirm=True")
        if not operator.strip():
            raise ValueError("reset_breaker needs the operator's name")
        was_active = self.state.circuit_breaker_active
        self.state.circuit_breaker_active = False
        self.state.breaker_needs_recovery = True
        logger.warning("circuit breaker reset by %s (was active: %s)", operator, was_active)

    def reset_peak_equity(self, *, confirm: bool, operator: str) -> None:
        """Explicit peak reset to current wallet. Separate from reset_breaker (RISK-04)."""
        if not confirm:
            raise ValueError("reset_peak_equity needs confirm=True")
        if not operator.strip():
            raise ValueError("reset_peak_equity needs the operator's name")
        self.state.peak_equity_usd = self.wallet_usd
        self.state.breaker_needs_recovery = False
        logger.warning("peak equity reset to %.2f by %s", self.wallet_usd, operator)

    def reset_daily(self) -> None:
        self.state.daily_pnl_usd = 0.0
