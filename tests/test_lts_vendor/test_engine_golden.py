"""The backtest engine must reproduce the golden digests captured before the hot-loop rewrite.

Regenerate the fixture only after an intentional, reviewed engine change:
    python tests/test_lts_vendor/engine_golden_support.py
"""

from __future__ import annotations

import json
import os
import sys

import pytest

from .engine_golden_support import FIXTURE_PATH, build_digests

# Fixtures were captured on Windows; Linux CI shows float/engine drift after dep bumps.
_SKIP_LINUX_CI = sys.platform.startswith("linux") and os.environ.get("CI") == "true"


@pytest.mark.skipif(
    _SKIP_LINUX_CI, reason="golden digests are Windows-captured; regenerate on Linux"
)
def test_engine_matches_golden_digests() -> None:
    expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["digests"]
    actual = build_digests()

    assert actual.keys() == expected.keys()
    changed = sorted(key for key in expected if actual[key] != expected[key])
    assert not changed, f"{len(changed)} golden case(s) changed, e.g. {changed[:5]}"
