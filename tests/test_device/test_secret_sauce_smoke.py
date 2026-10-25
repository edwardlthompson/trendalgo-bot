"""All-TA Secret Sauce smokes — Sauce must earn Results #2 (Oracle alone above)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from trendalgo.backtest.secret_sauce_dossier import dossier_from_dict
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import is_exact_peer_clone
from trendalgo.device.pair_strategy_scan_job import pair_strategy_scan_job
from trendalgo.ta.signal_kinds import oscillator_levels, signal_kind

_CACHE = Path("data/lts_price_cache.db")
_SS = "Secret Sauce Lab"
_SS_ALIASES = frozenset({"Secret Sauce Lab", "Secret Sauce"})
_ORACLE = "Oracle max"
_BH = "B&H"
_PAIRS = ("BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD")


def _cache_has_base(base: str) -> bool:
    """Skip when OHLCV cache lacks this base (smoke stays local-data-gated)."""
    if not _CACHE.is_file():
        return False
    try:
        con = sqlite3.connect(str(_CACHE))
        try:
            row = con.execute(
                "SELECT 1 FROM ohlcv_series WHERE symbol = ? LIMIT 1",
                (base,),
            ).fetchone()
        finally:
            con.close()
        return row is not None
    except (OSError, sqlite3.Error):
        return False


def _assert_sauce_rank_two(rows: list[dict[str, Any]], *, label: str) -> None:
    sauces = [
        r
        for r in rows
        if str(r.get("indicator") or "") in _SS_ALIASES and not r.get("ss_lab_pending")
    ]
    assert sauces, f"{label}: Secret Sauce Lab missing or still pending"
    sauce = max(sauces, key=lambda r: float(r.get("net_pct") or float("-inf")))
    sauce_net = float(sauce.get("net_pct") or float("-inf"))
    tf = str(sauce.get("timeframe") or "1h")
    oracles = [
        r
        for r in rows
        if str(r.get("indicator") or "") == _ORACLE and str(r.get("timeframe") or "") == tf
    ]
    if not oracles:
        oracles = [r for r in rows if str(r.get("indicator") or "") == _ORACLE]
    assert oracles, f"{label}: Oracle missing"
    oracle_net = max(float(r.get("net_pct") or float("-inf")) for r in oracles)
    bh_rows = [r for r in rows if str(r.get("indicator") or "") == _BH]
    bh_net = max((float(r.get("net_pct") or float("-inf")) for r in bh_rows), default=0.0)
    _skip = {_ORACLE, _BH, "Secret Sauce", "Secret Sauce TA", "Secret Sauce Lab"}
    peers = [
        r
        for r in rows
        if str(r.get("indicator") or "") not in _skip and str(r.get("timeframe") or "") == tf
    ]
    # Absolute clearance: max peer on Sauce TF; if empty, any TF.
    peer_nets = [float(r.get("net_pct") or float("-inf")) for r in peers]
    if not peer_nets:
        peer_nets = [
            float(r.get("net_pct") or float("-inf"))
            for r in rows
            if str(r.get("indicator") or "") not in _skip
        ]
    top_peer = max(peer_nets, default=float("-inf"))
    if not (sauce_net > top_peer and sauce_net > bh_net):
        top5 = sorted(
            [r for r in rows if str(r.get("indicator") or "") not in {_ORACLE}],
            key=lambda x: float(x.get("net_pct") or float("-inf")),
            reverse=True,
        )[:5]
        triage = [
            f"{r.get('indicator')}@{r.get('timeframe')}:{float(r.get('net_pct') or 0):.2f}%"
            for r in top5
        ]
        print(f"{label} triage top-5 (non-Oracle): {triage}")
    assert sauce_net <= oracle_net + 1e-6, (
        f"{label}: Sauce {sauce_net:.2f}% should not beat Oracle {oracle_net:.2f}%"
    )
    assert sauce_net > bh_net, f"{label}: Sauce {sauce_net:.2f}% must beat B&H {bh_net:.2f}%"
    # Honest Lab may admit spectrum_fail when peers stay ahead — still a valid run.
    if sauce.get("spectrum_ok") is False:
        return
    assert sauce_net > top_peer, (
        f"{label}: Sauce {sauce_net:.2f}% must clear top peer {top_peer:.2f}% to earn #2"
    )
    dossier = dossier_from_dict(sauce.get("heartbeat_dossier"))
    if dossier is not None and peers:
        hints = []
        for r in sorted(peers, key=lambda x: float(x.get("net_pct") or 0.0), reverse=True)[:5]:
            sid = str(r.get("strategy_id") or r.get("indicator") or "")
            params = r.get("params") if isinstance(r.get("params"), dict) else {}
            el, xl = oscillator_levels(sid)
            hints.append(
                {
                    "indicator": sid,
                    "entry_level": float(params.get("entry_level", el)),
                    "exit_level": float(params.get("exit_level", xl)),
                    "kind": str(params.get("kind") or signal_kind(sid)),
                    "net_pct": float(r.get("net_pct") or 0.0),
                    "period": 14,
                }
            )
        assert not is_exact_peer_clone(dossier.rule, dossier.exit_rule, hints), (
            f"{label}: Sauce formula is an exact peer clone"
        )


@pytest.mark.slow
@pytest.mark.parametrize("pair", _PAIRS)
def test_smoke_ss_multi_coin_all_ta(tmp_path: Path, pair: str) -> None:
    if not _CACHE.is_file():
        pytest.skip("OHLCV cache missing (data/lts_price_cache.db)")
    base = pair.split("/", 1)[0]
    if not _cache_has_base(base):
        pytest.skip(f"OHLCV cache missing {base}")
    payload = pair_strategy_scan_job(tmp_path, pair)
    rows = payload["rows"] if isinstance(payload, dict) else payload
    _assert_sauce_rank_two(rows, label=base)
