"""W-OCI4 installer: the image must match a pinned SHA-256, and sizing warnings never block."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from trendalgo.botd.installer import (
    InstallRefused,
    ReleasePin,
    detect_mem_gb,
    load_pin,
    main,
    sha256_file,
    sizing_warnings,
    verify_image,
)

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docker" / "botd-release.json"
GOOD = b"trendalgo-botd image bytes"
GOOD_SHA = hashlib.sha256(GOOD).hexdigest()


def _manifest(tmp_path: Path, sha: object) -> Path:
    path = tmp_path / "release.json"
    path.write_text(json.dumps({"version": "1.0.0", "image_sha256": sha}), encoding="utf-8")
    return path


def _image(tmp_path: Path, data: bytes = GOOD) -> Path:
    path = tmp_path / "botd.tar"
    path.write_bytes(data)
    return path


def test_the_shipped_manifest_has_no_pin_so_every_install_is_refused() -> None:
    assert load_pin(MANIFEST).image_sha256 is None


@pytest.mark.parametrize("raw", ["abc", "g" * 64, 12345, None, ""])
def test_a_malformed_or_missing_pin_counts_as_no_pin(tmp_path: Path, raw: object) -> None:
    assert load_pin(_manifest(tmp_path, raw)).image_sha256 is None


def test_an_upper_case_pin_is_read_in_lower_case(tmp_path: Path) -> None:
    assert load_pin(_manifest(tmp_path, GOOD_SHA.upper())).image_sha256 == GOOD_SHA


def test_no_pin_means_the_install_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InstallRefused, match="no pinned SHA-256"):
        verify_image(ReleasePin(version="1.0.0", image_sha256=None), _image(tmp_path))


def test_an_archive_matching_the_pin_is_accepted(tmp_path: Path) -> None:
    verify_image(ReleasePin(version="1.0.0", image_sha256=GOOD_SHA), _image(tmp_path))


def test_an_archive_that_differs_from_the_pin_is_refused(tmp_path: Path) -> None:
    pin = ReleasePin(version="1.0.0", image_sha256=GOOD_SHA)
    with pytest.raises(InstallRefused, match="does not match"):
        verify_image(pin, _image(tmp_path, b"tampered bytes"))


def test_the_digest_is_computed_in_chunks(tmp_path: Path) -> None:
    data = b"x" * (2 * (1 << 20) + 17)
    assert sha256_file(_image(tmp_path, data)) == hashlib.sha256(data).hexdigest()


def test_a_host_within_the_always_free_limit_gets_no_warning() -> None:
    assert sizing_warnings(2, 12.0) == []


def test_a_host_with_four_cpus_gets_a_sizing_warning() -> None:
    warnings = sizing_warnings(4, 12.0)
    assert len(warnings) == 1
    assert "4 CPUs" in warnings[0]


def test_a_host_over_the_memory_limit_gets_a_sizing_warning() -> None:
    warnings = sizing_warnings(2, 16.0)
    assert len(warnings) == 1
    assert "16.0 GB" in warnings[0]


def test_unknown_memory_is_flagged_for_a_manual_check() -> None:
    warnings = sizing_warnings(2, None)
    assert len(warnings) == 1
    assert "not detected" in warnings[0]


def test_memory_is_read_from_meminfo_in_gigabytes(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemFree:  1 kB\nMemTotal:       16777216 kB\n", encoding="ascii")
    assert detect_mem_gb(meminfo) == 16.0


def test_a_missing_or_garbled_meminfo_reports_no_memory(tmp_path: Path) -> None:
    assert detect_mem_gb(tmp_path / "absent") is None
    garbled = tmp_path / "garbled"
    garbled.write_text("MemTotal: lots kB\n", encoding="ascii")
    assert detect_mem_gb(garbled) is None


def test_the_cli_refuses_an_unpinned_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--manifest", str(_manifest(tmp_path, None)), "--image", str(_image(tmp_path))])
    assert code == 1
    assert "install refused" in capsys.readouterr().err


def test_the_cli_accepts_the_archive_that_matches_the_pin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = _manifest(tmp_path, GOOD_SHA)
    code = main(["--manifest", str(manifest), "--image", str(_image(tmp_path))])
    assert code == 0
    assert "verified" in capsys.readouterr().out


def test_the_cli_refuses_a_missing_archive_or_a_broken_manifest(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, GOOD_SHA)
    assert main(["--manifest", str(manifest), "--image", str(tmp_path / "nope.tar")]) == 1
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert main(["--manifest", str(broken), "--image", str(_image(tmp_path))]) == 1
