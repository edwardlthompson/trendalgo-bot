"""Extra CLI handlers for share-png / mutate (keeps __main__ under line limit)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run_share_png(
    root: Path,
    kind: str,
    *,
    lane: str,
    pair: str,
    dest: Path | str | None = None,
    pairs: list[str] | None = None,
    title: str | None = None,
    filters: dict[str, Any] | None = None,
    include_market_context: bool = True,
) -> dict[str, Any]:
    from trendalgo.results_store.desk_share import (
        share_board_png,
        share_dashboard_png,
        share_strategy_png,
    )

    if kind == "board":
        return share_board_png(
            root,
            lane=lane,
            dest=dest,
            pairs=pairs,
            title=title,
            filters=filters,
            include_market_context=include_market_context,
        )
    if kind == "dashboard":
        return share_dashboard_png(root, dest=dest)
    return share_strategy_png(root, pair=pair, lane=lane, dest=dest)


def run_mutate(
    root: Path, *, toggle_watch: bool, pair: str, lane: str, indicator: str
) -> dict[str, Any]:
    from trendalgo.results_store.desk_board import create_bot_from_fields
    from trendalgo.results_store.desk_board import toggle_watch as tw

    if toggle_watch:
        return tw(root, pair, lane=lane)
    return create_bot_from_fields(root, pair=pair, indicator=indicator)


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload))
