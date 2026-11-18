"""LIVE-05 Study honesty labels (kept out of the main study dialog for file limits)."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel

from trendalgo.botd.study_honesty import format_param_diff, separate_study_nets
from trendalgo.device import strings as S


def honesty_labels(row: dict[str, Any], coin: dict[str, Any] | None) -> list[QLabel]:
    raw_refit = row.get("refit_net_pct")
    refit = float(raw_refit if raw_refit is not None else row.get("net_pct") or 0.0)
    live_raw = row.get("live_net_pct")
    if live_raw is None and isinstance(coin, dict):
        live_raw = coin.get("live_net_pct")
    live_f = float(live_raw) if live_raw is not None else None
    separate_study_nets(refit_net_pct=refit, live_net_pct=live_f)
    live_txt = "—" if live_f is None else f"{live_f:.2f}%"
    labels = [
        QLabel(S.SECRET_SAUCE_STUDY_REFIT_NET.format(refit=refit)),
        QLabel(S.SECRET_SAUCE_STUDY_LIVE_NET.format(live=live_txt)),
        QLabel(S.SECRET_SAUCE_STUDY_NET_DISCLAIMER),
    ]
    if bool(row.get("ss_unavailable")):
        labels.insert(0, QLabel(S.SECRET_SAUCE_UNAVAILABLE))
    proxy_lbl = _oracle_proxy_label(row, coin)
    if proxy_lbl is not None:
        labels.insert(0, proxy_lbl)
    old = row.get("params_before") if isinstance(row.get("params_before"), dict) else None
    new = row.get("params") if isinstance(row.get("params"), dict) else None
    evidence = (
        row.get("holdout_evidence") if isinstance(row.get("holdout_evidence"), dict) else None
    )
    reg = row.get("regime")
    axis_fallback = reg.get("structural") if isinstance(reg, dict) else None
    axis = str(row.get("regime_axis") or axis_fallback or "—")
    if isinstance(old, dict) and isinstance(new, dict) and isinstance(evidence, dict):
        diff = format_param_diff(old=old, new=new, regime_axis=axis, holdout_evidence=evidence)
        labels.append(QLabel(S.SECRET_SAUCE_STUDY_PARAM_DIFF.format(diff=diff)))
    for lbl in labels:
        lbl.setWordWrap(True)
        lbl.setObjectName("hint")
    return labels


def _oracle_proxy_label(row: dict[str, Any], coin: dict[str, Any] | None) -> QLabel | None:
    oracle = None
    if isinstance(coin, dict):
        raw = coin.get("backtest_oracle_max")
        if isinstance(raw, dict):
            oracle = raw
        else:
            tops = coin.get("backtest_top_strategies")
            if isinstance(tops, list):
                oracles = [
                    r for r in tops if isinstance(r, dict) and r.get("indicator") == "Oracle max"
                ]
                if oracles:
                    oracle = max(oracles, key=lambda r: float(r.get("net_pct") or float("-inf")))
    if oracle is None:
        return None
    try:
        ceiling = float(oracle.get("net_pct") or 0.0)
        tradable = float(oracle["tradable_net_pct"])
    except (TypeError, ValueError, KeyError):
        return None
    sauce_txt = "—"
    try:
        if row.get("net_pct") is not None:
            sauce_txt = f"{float(row['net_pct']):.2f}%"
    except (TypeError, ValueError):
        sauce_txt = "—"
    return QLabel(
        S.SECRET_SAUCE_STUDY_ORACLE_PROXY.format(
            ceiling=ceiling, tradable=tradable, sauce=sauce_txt
        )
    )
