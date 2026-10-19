"""Baseline Results concepts (not TA catalog strategies)."""

from __future__ import annotations

BASELINE_GLOSSARY_ENTRIES: list[dict[str, str | list[str]]] = [
    {
        "id": "oracle-max",
        "category": "Baselines",
        "title": "Oracle max",
        "short": (
            "Hindsight ceiling — the most a trader could have made over the window "
            "with flawless trough-to-peak timing."
        ),
        "long": (
            "Oracle max is not a live strategy. It is the fee-aware Net % ceiling if every "
            "confirmed trough-to-peak swing in the backtest window had been taken perfectly. "
            "No causal indicator can equal it; Secret Sauce and catalog strategies aim below "
            "this bar. Use it to judge how much edge remains on the tape, not as a bot recipe."
        ),
        "formula": "sum(perfect_swing_net_after_fees) / stake → Net %",
        "related": ["B&H", "Secret Sauce"],
    },
]
