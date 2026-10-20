"""Decide one launch prompt: donate nudge or Download-and-install update."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import time

from trendalgo.device.about.github_release import (
    GithubRelease,
    fetch_latest_github_release,
    release_page_url,
)
from trendalgo.device.about.product_update import (
    DEFAULT_ASSET_PREFIX,
    preview_release_notes,
    select_product_asset,
    should_check_daily,
    should_nudge_donate,
    should_prompt_update,
)
from trendalgo.device.about.update_prefs import (
    load_update_prefs,
    mark_update_checked,
    mark_version_seen,
)
from trendalgo.device.github_feedback.release_repo import load_release_repo


@dataclass(frozen=True)
class LaunchPrompt:
    kind: str
    version: str = ""
    url: str = ""
    changelog: str = ""


@dataclass(frozen=True)
class UpdateCheckResult:
    """Manual About check: distinguish update / current / fetch error / donate."""

    status: str  # "update" | "current" | "error" | "donate"
    prompt: LaunchPrompt | None = None


FetchLatest = Callable[[str, str], GithubRelease | None]


def decide_launch_prompt(
    root: Path,
    *,
    current_version: str,
    now: float | None = None,
    release_repo: str | None = None,
    user_agent: str = "TrendAlgo/0",
    fetch_latest: FetchLatest | None = None,
    interval: str = "launch",
    prefix: str = DEFAULT_ASSET_PREFIX,
    kind: str = "exe",
    force: bool = False,
) -> LaunchPrompt | None:
    result = check_for_update(
        root,
        current_version=current_version,
        now=now,
        release_repo=release_repo,
        user_agent=user_agent,
        fetch_latest=fetch_latest,
        interval=interval,
        prefix=prefix,
        kind=kind,
        force=force,
    )
    if result.status in {"update", "donate"}:
        return result.prompt
    return None


def check_for_update(
    root: Path,
    *,
    current_version: str,
    now: float | None = None,
    release_repo: str | None = None,
    user_agent: str = "TrendAlgo/0",
    fetch_latest: FetchLatest | None = None,
    interval: str = "launch",
    prefix: str = DEFAULT_ASSET_PREFIX,
    kind: str = "exe",
    force: bool = False,
) -> UpdateCheckResult:
    clock = time() * 1000 if now is None else now
    prefs = load_update_prefs(root)
    if should_nudge_donate(prefs.last_seen_version, current_version):
        return UpdateCheckResult("donate", LaunchPrompt(kind="donate"))
    mark_version_seen(root, current_version)
    if interval == "off":
        return UpdateCheckResult("current")
    if interval == "daily" and not should_check_daily(prefs.last_check_at, clock):
        return UpdateCheckResult("current")
    repo = release_repo if release_repo is not None else load_release_repo()
    do_fetch = fetch_latest or (
        lambda ver, r: fetch_latest_github_release(ver, r, user_agent=user_agent)
    )
    release = do_fetch(current_version, repo)
    mark_update_checked(root, clock)
    if release is None:
        return UpdateCheckResult("error")
    asset = select_product_asset(list(release.assets), kind=kind, prefix=prefix)
    latest = asset[0] if asset else None
    dismissed = None if force else prefs.dismissed_version
    if not should_prompt_update(current_version, latest, dismissed) or not latest:
        return UpdateCheckResult("current")
    url = asset[1] if asset else (release.html_url or release_page_url(repo))
    prompt = LaunchPrompt(
        kind="update",
        version=latest,
        url=url,
        changelog=preview_release_notes(release.body),
    )
    return UpdateCheckResult("update", prompt)
