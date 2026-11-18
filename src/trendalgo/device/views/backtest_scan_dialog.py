"""Backtest wrapper around shared ScanProgressDialog."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QWidget

from trendalgo.device import strings as S
from trendalgo.device.backtest_scan_eta import prior_seconds
from trendalgo.device.pair_strategy_scan import SAUCE_PROGRESS_STEPS
from trendalgo.device.scan_time_history import ScanTimeHistory, load_history
from trendalgo.device.views.scan_progress_dialog import (
    ScanProgressDialog,
    apply_main_blur,
)

__all__ = ["BacktestScanDialog", "apply_main_blur"]


class BacktestScanDialog(ScanProgressDialog):
    """Blocking verbose progress while All-TA runs (single pair)."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        pair: str,
        n_strategies: int,
        n_timeframes: int,
        had_subhour: bool,
        on_cancel: Callable[[], None],
        root: Any = None,
    ) -> None:
        hist = load_history(root) if root is not None else ScanTimeHistory()
        n_strat = max(0, int(n_strategies))
        n_tf = max(0, int(n_timeframes))
        prior = prior_seconds(
            hist, n_strategies=n_strat, n_timeframes=n_tf, had_subhour=bool(had_subhour)
        )
        total = max(1, n_strat * max(1, n_tf)) + int(SAUCE_PROGRESS_STEPS)
        seed = S.BACKTEST_SCAN_SEED.format(
            pair=pair,
            n_tf=n_tf,
            n_strat=n_strat,
            subhour=S.BACKTEST_SCAN_SUBHOUR if had_subhour else "",
        )
        super().__init__(
            parent,
            title=S.BACKTEST_SCAN_TITLE.format(pair=pair),
            seed_lines=(seed, S.SCAN_PROGRESS_STARTING),
            on_cancel=on_cancel,
            prior_s=prior,
            initial_total=total,
            initial_pair=pair,
            initial_pairs_total=1,
            count_label=S.BACKTEST_SCAN_STRATEGIES_FMT,
        )
        self._pair = pair

    def update_progress(self, raw: dict[str, Any] | None, *, worker_ready: bool = False) -> None:
        payload = dict(raw) if isinstance(raw, dict) else {}
        payload.setdefault("current_pair", self._pair)
        payload.setdefault("pairs_total", 1)
        # Still running → 0 done; finished paint happens after close.
        if "pairs_done" not in payload:
            payload["pairs_done"] = 1 if worker_ready else 0
        super().update_progress(payload, worker_ready=worker_ready)
