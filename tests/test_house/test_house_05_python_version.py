"""HOUSE-05: requires-python matches README (3.12 only; not 3.13+)."""

from __future__ import annotations

import re
from pathlib import Path


def test_requires_python_matches_readme() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    match = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject)
    assert match is not None
    assert match.group(1) == ">=3.12,<3.13"
    assert "3.12" in readme
    assert "not 3.13+" in readme
