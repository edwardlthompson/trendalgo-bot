"""Pinned multi-lane ETA + Auto-scan toggles for Scan/Backtest settings."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from trendalgo.brokers.forex_universe import load_forex_universe
from trendalgo.brokers.tradfi_universe import load_tradfi_universe
from trendalgo.device import strings as S
from trendalgo.device.lane_prefs import LanePrefs, load_lane_prefs, save_lane_prefs
from trendalgo.device.lane_scan_filters import load_lane_scan_filters
from trendalgo.device.lts_scan_model import load_filters
from trendalgo.device.scan_eta_filters import META_FUNNEL, projected_scan_coins
from trendalgo.device.scan_time_history import estimate_label, estimate_scan_seconds, load_history
from trendalgo.device.views.lane_toggles import LaneToggles

__all__ = ["ScanBtEtaHeader"]


class ScanBtEtaHeader(QFrame):
    """Non-collapsible ETA block: per-desk estimates + grand total + auto-scan toggles."""

    def __init__(
        self,
        root: Path,
        *,
        crypto_n: int = 1,
        on_auto_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = root
        self._crypto_n = max(1, int(crypto_n))
        self._on_auto_changed = on_auto_changed
        self.setObjectName("scanBtEtaHeader")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        title = QLabel(S.SCAN_BT_ETA_TITLE)
        title.setObjectName("sectionTitle")
        self._crypto = QLabel()
        self._tradfi = QLabel()
        self._forex = QLabel()
        self._total = QLabel()
        self._note = QLabel(S.SCAN_BT_ETA_LANE_NOTE)
        self._note.setObjectName("hint")
        self._note.setWordWrap(True)
        for lab in (self._crypto, self._tradfi, self._forex, self._total):
            lab.setObjectName("hint")
            lab.setWordWrap(True)

        prefs = load_lane_prefs(root)
        self._toggles = LaneToggles(prefs, on_changed=self._on_toggles)
        auto_title = QLabel(S.SCAN_BT_AUTO_SECTION)
        auto_title.setObjectName("sectionTitle")

        col = QVBoxLayout(self)
        col.setContentsMargins(10, 8, 10, 8)
        col.setSpacing(4)
        col.addWidget(title)
        col.addWidget(self._crypto)
        col.addWidget(self._tradfi)
        col.addWidget(self._forex)
        col.addWidget(self._total)
        col.addWidget(self._note)
        row = QHBoxLayout()
        row.addWidget(auto_title)
        row.addStretch(1)
        col.addLayout(row)
        col.addWidget(self._toggles)

    def lane_prefs(self) -> LanePrefs:
        return self._toggles.prefs()

    def set_status(self, text: str) -> None:
        self._note.setText(text or S.SCAN_BT_ETA_LANE_NOTE)

    def _on_toggles(self, prefs: LanePrefs) -> None:
        save_lane_prefs(self._root, prefs)
        self.refresh()
        if self._on_auto_changed is not None:
            self._on_auto_changed()

    def refresh(
        self,
        *,
        n_strategies: int = 1,
        n_timeframes: int = 1,
        had_subhour: bool = False,
        market_context: bool = True,
        sauce_with_scan: bool = False,
        sauce_top_n: int = 0,
        min_volume_usd: float = 0.0,
        require_continuous_1h: bool = True,
        tradfi_top_n: int | None = None,
    ) -> None:
        hist = load_history(self._root)
        prefs = self._toggles.prefs()
        crypto_n = self._crypto_coins(min_volume_usd, require_continuous_1h)
        # All-TA bound = top_n survivors; bar fetch uses full live/seed universe.
        uni_n = max(1, len(load_tradfi_universe(root=self._root)))
        lane_f = load_lane_scan_filters(self._root, "tradfi")
        top = tradfi_top_n if tradfi_top_n is not None else lane_f.top_n
        tf_n = max(1, int(top) if top and int(top) > 0 else uni_n)
        fx_n = max(1, len(load_forex_universe()))

        def _line(name: str, n: int) -> tuple[str, float]:
            label = estimate_label(
                hist,
                n_strategies=n_strategies,
                n_timeframes=n_timeframes,
                had_subhour=had_subhour,
                n_coins=n,
                market_context=market_context,
                sauce_with_scan=sauce_with_scan,
                sauce_top_n=sauce_top_n,
            )
            _c, _m, _s, total = estimate_scan_seconds(
                hist,
                n_strategies=n_strategies,
                n_timeframes=n_timeframes,
                had_subhour=had_subhour,
                n_coins=n,
                market_context=market_context,
                sauce_with_scan=sauce_with_scan,
                sauce_top_n=sauce_top_n,
            )
            return f"{name}: {label}", total

        c_txt, c_s = _line(S.SCAN_BT_ETA_CRYPTO, crypto_n)
        t_txt, t_s = _line(S.SCAN_BT_ETA_TRADFI, tf_n)
        f_txt, f_s = _line(S.SCAN_BT_ETA_FOREX, fx_n)
        self._crypto.setText(c_txt)
        self._tradfi.setText(t_txt)
        self._forex.setText(f_txt)
        grand = 0.0
        if prefs.auto_scan_crypto:
            grand += c_s
        if prefs.auto_scan_tradfi:
            grand += t_s
        if prefs.auto_scan_forex:
            grand += f_s
        self._total.setText(f"{S.SCAN_BT_ETA_TOTAL}: ~{_fmt_duration(grand)}")

    def _crypto_coins(self, min_volume_usd: float, require_continuous_1h: bool) -> int:
        saved = load_filters(self._root, lane="crypto")
        funnel = saved.get(META_FUNNEL) if isinstance(saved.get(META_FUNNEL), dict) else None
        return projected_scan_coins(
            funnel,
            min_volume_usd=min_volume_usd,
            require_continuous_1h=require_continuous_1h,
            fallback_n=self._crypto_n,
        )


def _fmt_duration(seconds: float) -> str:
    s = max(0.0, float(seconds))
    if s < 90:
        return f"{s:.0f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.1f}h"
