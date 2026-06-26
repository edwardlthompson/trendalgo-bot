"""Position sizing, daily loss cap, and circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass, field

from trendalgo.risk.config import RiskLimits


@dataclass
class RiskState:
    daily_pnl_usd: float = 0.0
    peak_equity_usd: float = 0.0
    circuit_breaker_active: bool = False
    paused: bool = False


@dataclass
class RiskManager:
    limits: RiskLimits
    wallet_usd: float
    state: RiskState = field(default_factory=RiskState)

    def __post_init__(self) -> None:
        if self.state.peak_equity_usd <= 0:
            self.state.peak_equity_usd = self.wallet_usd

    def compute_stake(self, proposed_usd: float) -> float:
        pct_cap = self.wallet_usd * self.limits.max_stake_pct
        cap = min(self.limits.max_stake_usd, pct_cap)
        return round(max(0.0, min(proposed_usd, cap)), 2)

    def record_pnl(self, delta_usd: float) -> None:
        self.state.daily_pnl_usd += delta_usd
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
        self.state.paused = False
        self.state.circuit_breaker_active = False

    def reset_daily(self) -> None:
        self.state.daily_pnl_usd = 0.0
