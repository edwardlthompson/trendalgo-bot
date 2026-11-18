"""Offscreen Market Context graphics for PNG export (same painters as the live pane)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.buy_picks import rank_buy_picks
from trendalgo.device.market_context_export import context_is_ok
from trendalgo.device.views.buy_picks_gfx import ScoreSpectrum
from trendalgo.device.views.market_context_format import (
    levels_lines,
    risk_line,
    signal_line,
    structure_lines,
)
from trendalgo.device.views.market_context_gfx import (
    LevelsLadder,
    RiskBars,
    SignalGauge,
    StructureMeters,
)

_PAIR_W = 140


def build_context_gfx_band(ctx: dict[str, Any]) -> QWidget | None:
    """Four-module Market Context strip matching the Results pane graphics."""
    if not context_is_ok(ctx):
        return None
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    title = QLabel(S.MARKET_CTX_TITLE)
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    row = QWidget()
    row_lay = QHBoxLayout(row)
    row_lay.setContentsMargins(0, 0, 0, 0)
    row_lay.setSpacing(8)
    gauge, ladder, risk, meters = SignalGauge(), LevelsLadder(), RiskBars(), StructureMeters()
    gauge.set_data(ctx)
    ladder.set_data(ctx)
    risk.set_data(ctx)
    meters.set_data(ctx)
    lvl = levels_lines(ctx)
    compact = [line for line in lvl if line.startswith("Nearest") or "Confluence" in line]
    modules = (
        (S.MARKET_CTX_SIGNAL, gauge, signal_line(ctx)),
        (S.MARKET_CTX_LEVELS, ladder, "\n".join(compact) or "—"),
        (S.MARKET_CTX_RISK, risk, risk_line(ctx)),
        (S.MARKET_CTX_STRUCTURE, meters, "\n".join(structure_lines(ctx)[:4]) or "—"),
    )
    for head, gfx, caption in modules:
        row_lay.addWidget(_module(head, gfx, caption), 1)
    lay.addWidget(row)
    return root


def build_buy_picks_gfx_band(coins: list[dict[str, Any]]) -> QWidget | None:
    """Market Context top-10 band with ScoreSpectrum ticks (Qualified share)."""
    picks = rank_buy_picks(coins)
    if not picks:
        return None
    root = QWidget()
    lay = QVBoxLayout(root)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    title = QLabel(S.BUY_PICKS_TITLE)
    title.setObjectName("sectionTitle")
    lay.addWidget(title)
    grid_host = QFrame()
    grid_host.setObjectName("marketCtxModule")
    grid = QGridLayout(grid_host)
    grid.setContentsMargins(8, 6, 8, 6)
    grid.setHorizontalSpacing(10)
    grid.setVerticalSpacing(6)
    grid.setColumnMinimumWidth(0, _PAIR_W)
    headers = (
        S.BUY_PICKS_COL_PAIR,
        S.BUY_PICKS_COL_BIAS,
        S.BUY_PICKS_COL_SIGNAL,
        S.BUY_PICKS_COL_CONF,
        S.BUY_PICKS_COL_SCORE,
        S.BUY_PICKS_COL_NEAR,
        S.BUY_PICKS_COL_RR,
        S.BUY_PICKS_COL_LEVELS,
        S.BUY_PICKS_COL_TA,
    )
    for col, label in enumerate(headers):
        hdr = QLabel(label)
        hdr.setObjectName("hint")
        grid.addWidget(hdr, 0, col)
    for i, pick in enumerate(picks):
        _add_pick(grid, i + 1, pick)
    lay.addWidget(grid_host)
    return root


def _module(title: str, gfx: QWidget, caption: str) -> QFrame:
    card = QFrame()
    card.setObjectName("marketCtxModule")
    card.setMinimumHeight(200)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(8, 8, 8, 8)
    lay.setSpacing(4)
    head = QLabel(title)
    head.setObjectName("sectionTitle")
    text = QLabel(caption)
    text.setObjectName("hint")
    text.setWordWrap(True)
    lay.addWidget(head)
    lay.addWidget(gfx, 1)
    lay.addWidget(text)
    return card


def _add_pick(grid: QGridLayout, row: int, pick: dict[str, Any]) -> None:
    pair = QLabel(str(pick.get("pair") or pick.get("symbol") or "—"))
    pair.setObjectName("sectionTitle")
    pair.setMinimumWidth(_PAIR_W)
    spectrum = ScoreSpectrum()
    spectrum.setMinimumWidth(120)
    try:
        spectrum.set_score(float(pick.get("score") or 0.0))
    except (TypeError, ValueError):
        spectrum.set_score(0.0)
    rr, best = pick.get("rr_r1"), pick.get("bot_best_net_pct")
    try:
        rr_s = f"{float(rr):.2f}" if rr is not None else S.BUY_PICKS_TA_NONE
    except (TypeError, ValueError):
        rr_s = S.BUY_PICKS_TA_NONE
    try:
        ta = f"+{float(best):.1f}%" if best is not None else S.BUY_PICKS_TA_NONE
    except (TypeError, ValueError):
        ta = S.BUY_PICKS_TA_NONE
    texts = (
        str(pick.get("signal") or "Neutral"),
        str(int(float(pick.get("confidence") or 0))),
        f"{float(pick.get('score') or 0):.2f}",
        str(pick.get("nearest_sr") or "—"),
        rr_s,
        str(int(pick.get("confluence") or 0)),
        ta,
    )
    grid.addWidget(pair, row, 0)
    grid.addWidget(spectrum, row, 1)
    for col, text in enumerate(texts, start=2):
        lab = QLabel(text)
        lab.setObjectName("hint")
        grid.addWidget(lab, row, col)
