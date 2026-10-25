"""Buy picks pane headers, columns, and alignment."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from trendalgo.device import strings as S
from trendalgo.device.views.buy_picks_gfx import ScoreSpectrum
from trendalgo.device.views.buy_picks_pane import BuyPicksPane

_PICK_A = {
    "symbol": "BTC",
    "pair": "BTC/USD",
    "signal": "Buy",
    "score": 1.1,
    "confidence": 55.0,
    "nearest_sr": "S1",
    "rr_r1": 2.0,
    "confluence": 1,
    "regime": "Trending Up",
    "bot_best_net_pct": 6.5,
    "bot_best_label": "MFI 3h",
    "fallback": False,
}
_PICK_B = {
    "symbol": "USELESS",
    "pair": "USELESS/USD",
    "signal": "Neutral",
    "score": 0.32,
    "confidence": 16.0,
    "nearest_sr": "R1",
    "rr_r1": 1.71,
    "confluence": 1,
    "regime": "Range",
    "bot_best_net_pct": None,
    "bot_best_label": "",
    "fallback": True,
}


def test_pane_empty_and_headers(qtbot) -> None:
    pane = BuyPicksPane()
    qtbot.addWidget(pane)
    pane.show()
    pane.set_picks([])
    assert not pane._empty.isHidden()  # noqa: SLF001
    assert pane._list.isHidden()  # noqa: SLF001
    pane.set_picks([_PICK_A])
    assert pane._empty.isHidden()  # noqa: SLF001
    assert not pane._list.isHidden()  # noqa: SLF001
    assert len(pane.findChildren(ScoreSpectrum)) == 1
    headers = [
        w
        for w in pane._list.findChildren(QLabel)  # noqa: SLF001
        if w.toolTip()
        and w.text()
        in {
            S.BUY_PICKS_COL_PAIR,
            S.BUY_PICKS_COL_BIAS,
            S.BUY_PICKS_COL_SIGNAL,
            S.BUY_PICKS_COL_CONF,
            S.BUY_PICKS_COL_SCORE,
            S.BUY_PICKS_COL_NEAR,
            S.BUY_PICKS_COL_RR,
            S.BUY_PICKS_COL_LEVELS,
            S.BUY_PICKS_COL_TA,
        }
    ]
    assert len(headers) == 9
    assert all(h.toolTip().strip() for h in headers)


def test_pane_split_columns_and_align(qtbot) -> None:
    pane = BuyPicksPane()
    qtbot.addWidget(pane)
    pane.resize(1100, 320)
    pane.show()
    pane.set_picks([_PICK_A, _PICK_B])
    qtbot.waitExposed(pane)
    spectra = pane.findChildren(ScoreSpectrum)
    assert len(spectra) == 2
    xs = {s.mapTo(pane, s.rect().topLeft()).x() for s in spectra}
    assert len(xs) == 1
    texts = {lab.text() for lab in pane._list.findChildren(QLabel)}  # noqa: SLF001
    assert "Buy" in texts
    assert "55" in texts
    assert "1.10" in texts
    assert "2.00" in texts
    assert "USELESS/USD" in texts


def test_pane_collapse_callback(qtbot) -> None:
    seen: list[bool] = []
    pane = BuyPicksPane(expanded=True, on_collapse=seen.append)
    qtbot.addWidget(pane)
    pane.set_expanded(False)
    assert seen == [True]
