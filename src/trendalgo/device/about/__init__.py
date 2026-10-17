"""Quiet donate + silent daily installer check (GP-6)."""

from trendalgo.device.about.product_update import (
    compare_versions,
    should_check_daily,
    should_nudge_donate,
    should_prompt_update,
)

__all__ = [
    "compare_versions",
    "should_check_daily",
    "should_nudge_donate",
    "should_prompt_update",
]
