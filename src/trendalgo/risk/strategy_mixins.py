"""Native strategy mixins — risk guard and scale-in/out (CM-2)."""

from __future__ import annotations

from typing import Any

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.manager import RiskManager


class RiskGuardMixin:
    """Attach to native strategies; set `risk_manager` before signal evaluation."""

    risk_limits: RiskLimits = RiskLimits()
    risk_manager: RiskManager | None = None

    def _ensure_risk_manager(self, wallet_usd: float = 1000.0) -> RiskManager:
        if self.risk_manager is None:
            self.risk_manager = RiskManager(limits=self.risk_limits, wallet_usd=wallet_usd)
        return self.risk_manager

    def risk_custom_stake_amount(
        self,
        pair: str,
        current_time: Any,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float | None,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs: Any,
    ) -> float:
        mgr = self._ensure_risk_manager()
        ok, _ = mgr.can_open_trade()
        if not ok:
            return 0.0
        return mgr.compute_stake(proposed_stake)

    def risk_should_exit_daily_cap(self, pnl_delta: float) -> bool:
        mgr = self._ensure_risk_manager()
        mgr.record_pnl(pnl_delta)
        return not mgr.can_open_trade()[0]


class ScalePositionMixin:
    """Scale-in/out helpers for native runner position adjustments (T25, T36)."""

    exit_trailing_stop_pct: float = 0.03
    exit_scale_out_pct: float = 0.5
    exit_scale_in_enabled: bool = False
    exit_scale_out_enabled: bool = True

    def adjust_trade_position(
        self,
        trade: Any,
        current_time: Any,
        current_rate: float,
        current_profit: float,
        min_stake: float | None,
        max_stake: float | None,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs: Any,
    ) -> float | None:
        from trendalgo.risk.exit_rules import scale_position_amount

        floor = min_stake or 10.0
        if current_profit > 0 and self.exit_scale_out_enabled:
            return -scale_position_amount(
                trade.stake_amount, self.exit_scale_out_pct, min_stake=floor
            )
        if current_profit < 0 and self.exit_scale_in_enabled:
            return scale_position_amount(
                trade.stake_amount, self.exit_scale_out_pct, min_stake=floor
            )
        return None

    def custom_stoploss(
        self,
        pair: str,
        trade: Any,
        current_time: Any,
        current_rate: float,
        current_profit: float,
        **kwargs: Any,
    ) -> float | None:
        if current_profit > 0 and self.exit_trailing_stop_pct > 0:
            return -self.exit_trailing_stop_pct
        return None
