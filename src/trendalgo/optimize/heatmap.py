"""Hyperopt parameter sweep heatmap grid (T18)."""

from __future__ import annotations

from typing import Any


def hyperopt_heatmap_grid(
    param_x: str = "rsi_entry",
    param_y: str = "stoploss",
    x_values: list[float] | None = None,
    y_values: list[float] | None = None,
) -> dict[str, Any]:
    xs = x_values or [25, 30, 35, 40]
    ys = y_values or [-0.03, -0.05, -0.07, -0.1]
    cells: list[dict[str, float | str]] = []
    best = -999.0
    best_cell: dict[str, float | str] = {}
    for x in xs:
        for y in ys:
            score = (x / 40) * 10 + abs(y) * 50
            cell = {"x": x, "y": y, "score": round(score, 2)}
            cells.append(cell)
            if score > best:
                best = score
                best_cell = cell
    return {
        "param_x": param_x,
        "param_y": param_y,
        "cells": cells,
        "best": best_cell,
    }
