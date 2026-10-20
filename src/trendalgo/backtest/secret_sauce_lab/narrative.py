"""English narrative for Secret Sauce Lab winners."""

from __future__ import annotations

from trendalgo.backtest.oracle_pattern_mine import CompositeRule
from trendalgo.backtest.secret_sauce_dossier import formula_english
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot

_FAMILY_BLURB = {
    "dip_uptrend": "Uptrend dip-buy — catch pullbacks without fighting the trend.",
    "mean_reversion": "Range mean-reversion — fade extremes while the tape is quiet.",
    "osc_cross": "Oscillator cross edges — enter/exit on crosses, not level-state.",
    "momentum": "Momentum continuation — ride strength with a soft exit.",
    "squeeze_breakout": "Squeeze release — compression then expansion.",
    "volume_impulse": "Volume impulse — participation confirms the move.",
    "classic": "Classic TA seed — RSI/stoch levels under fee-aware search.",
    "peer_inspire": "Peer-inspired neighborhood — mutated levels/gates, not a catalog clone.",
    "oracle_pattern": "Fitted on Oracle swing bars (causal features), fee-ranked toward Oracle Net %.",
    "peer_pattern": "Fitted on top-peer trade bars (causal features), fee-ranked toward Oracle Net %.",
    "rsx_neighborhood": (
        "Cross-period RSX entry/exit grid around the peer (catalog-parity crosses); "
        "fee-max toward Oracle, never an exact same-period photocopy."
    ),
    "peer_reexpress": "Catalog-parity re-sim of top peer edge in Sauce language — interim when no superior distinct recipe clears Results #2.",
    "residual_and": "Residual AND — one extra causal conjunct on missed Oracle bars; fee re-sim required.",
    "adaptive_exit": "Adaptive exit — peak/structure/oscillator exits searched against a strong entry.",
}


def build_narrative(
    regime: RegimeSnapshot,
    *,
    family: str,
    entry: CompositeRule,
    exit_rule: CompositeRule,
    beat_bh: bool,
) -> tuple[str, str]:
    """Return (formula_en, anti_cheat_blurb)."""
    formula = formula_english(entry, exit_rule)
    blurb = _FAMILY_BLURB.get(family, "Lab P&L search.")
    bh_note = (
        "Beat Buy & Hold on this window."
        if beat_bh
        else "Did not clear Buy & Hold — still shown honestly."
    )
    anti = (
        f"Secret Sauce Lab · {regime.narrative}. Family={family}. {blurb} "
        f"{bh_note} Objective: maximize fee Net % toward Oracle ceiling; "
        f"top peer is the floor not the target. Causal features only; "
        f"fitted on swing/peer-trade bars, never enter-at-oracle-index."
    )
    return formula, anti
