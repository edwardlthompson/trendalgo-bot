"""Version / update checker stub (OPS5)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def check_github_release(repo: str | None = None) -> dict[str, str | bool]:
    slug = repo or os.environ.get("GITHUB_RELEASE_REPO", "")
    if not slug or "/" not in slug:
        return {"ok": False, "reason": "no repo configured"}
    url = f"https://api.github.com/repos/{slug}/releases/latest"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "tag": str(data.get("tag_name", "")), "url": str(data.get("html_url", ""))}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {"ok": False, "reason": "fetch failed"}
