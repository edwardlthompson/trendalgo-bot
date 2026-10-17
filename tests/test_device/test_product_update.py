"""Product update rules: daily window, asset parse, donate nudge, update prompt."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.about.github_release import GithubRelease
from trendalgo.device.about.product_update import (
    MS_DAY,
    NamedAsset,
    is_newer_version,
    parse_asset_version,
    select_product_asset,
    should_check_daily,
    should_nudge_donate,
    should_prompt_update,
)
from trendalgo.device.about.run_updates import decide_launch_prompt


def test_should_check_daily() -> None:
    assert should_check_daily(None, 1000) is True
    assert should_check_daily(1000, 1000 + MS_DAY) is True
    assert should_check_daily(1000, 1000 + MS_DAY - 1) is False


def test_is_newer_version() -> None:
    assert is_newer_version("0.6.0", "0.6.2") is True
    assert is_newer_version("0.6.2", "0.6.2") is False


def test_parse_and_select_exe_asset() -> None:
    assert parse_asset_version("TrendAlgo-0.7.0-x64-setup.exe", kind="exe", prefix="TrendAlgo") == (
        "0.7.0"
    )
    picked = select_product_asset(
        [NamedAsset("TrendAlgo-0.7.0-x64-setup.exe", "https://example/a.exe")],
        kind="exe",
        prefix="TrendAlgo",
    )
    assert picked == ("0.7.0", "https://example/a.exe")


def test_should_nudge_donate_and_prompt_update() -> None:
    assert should_nudge_donate(None, "0.6.2") is False
    assert should_nudge_donate("0.6.0", "0.6.2") is True
    assert should_prompt_update("0.6.0", "0.7.0", None) is True
    assert should_prompt_update("0.6.0", "0.7.0", "0.7.0") is False


def test_decide_launch_prompt_donate_then_update(tmp_path: Path) -> None:
    from trendalgo.device.about.update_prefs import mark_version_seen

    mark_version_seen(tmp_path, "0.6.0")
    assert decide_launch_prompt(tmp_path, current_version="0.6.2").kind == "donate"  # type: ignore[union-attr]

    def fetch(_ver: str, _repo: str) -> GithubRelease:
        return GithubRelease(
            "https://github.com/acme/app/releases/tag/v0.7.0",
            (NamedAsset("TrendAlgo-0.7.0-x64-setup.exe", "https://example/a.exe"),),
        )

    mark_version_seen(tmp_path, "0.6.2")
    prompt = decide_launch_prompt(
        tmp_path,
        current_version="0.6.2",
        now=MS_DAY * 2,
        release_repo="acme/app",
        fetch_latest=fetch,
    )
    assert prompt is not None
    assert prompt.kind == "update"
    assert prompt.version == "0.7.0"
