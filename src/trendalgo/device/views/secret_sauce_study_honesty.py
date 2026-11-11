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
