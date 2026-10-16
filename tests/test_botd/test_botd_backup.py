"""H5 backup: nightly snapshots are integrity-checked, and a restore reproduces plan and positions."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.botd.backup import BackupError, integrity_ok, restore, snapshot
from trendalgo.botd.host_store import HostStore


def _live(tmp_path: Path) -> HostStore:
    store = HostStore(tmp_path / "live" / "host.db")
    store.save_plan(plan_version=3, bundle_hash="h3", body='{"bots":[1]}')
    store.save_position("bot-1", '{"qty":1.5}')
    return store


def test_a_snapshot_is_written_as_an_integrity_checked_copy(tmp_path: Path) -> None:
    live = _live(tmp_path)
    written = snapshot([live.db_path], tmp_path / "snaps", stamp="20261009")
    assert written == [tmp_path / "snaps" / "host-20261009.db"]
    assert integrity_ok(written[0])


def test_a_restore_brings_back_the_plan_version_and_positions(tmp_path: Path) -> None:
    live = _live(tmp_path)
    (snap,) = snapshot([live.db_path], tmp_path / "snaps", stamp="s1")
    live.save_plan(plan_version=4, bundle_hash="h4", body="{}")
    live.save_position("bot-1", '{"qty":9}')
    restore(snap, live.db_path)
    restored = HostStore(live.db_path)
    plan = restored.plan()
    assert plan is not None and plan["plan_version"] == 3
    assert restored.positions() == {"bot-1": '{"qty":1.5}'}


def test_a_missing_source_is_skipped_and_the_folder_still_created(tmp_path: Path) -> None:
    dest = tmp_path / "snaps"
    assert snapshot([tmp_path / "absent.db"], dest, stamp="s") == []
    assert dest.is_dir()


def test_a_corrupt_snapshot_is_refused_and_the_target_is_left_alone(tmp_path: Path) -> None:
    live = _live(tmp_path)
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"this is not a database" * 64)
    before = live.db_path.read_bytes()
    with pytest.raises(BackupError, match="integrity"):
        restore(bad, live.db_path)
    assert live.db_path.read_bytes() == before


def test_a_file_that_is_not_a_database_is_refused_at_snapshot_time(tmp_path: Path) -> None:
    junk = tmp_path / "junk.db"
    junk.write_bytes(b"x" * 200)
    with pytest.raises(BackupError):
        snapshot([junk], tmp_path / "snaps", stamp="s")
    assert not (tmp_path / "snaps" / "junk-s.db").exists()


def test_integrity_check_never_creates_a_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    assert integrity_ok(missing) is False
    assert not missing.exists()


def test_a_restore_clears_the_old_wal_and_shm_sidecars(tmp_path: Path) -> None:
    live = _live(tmp_path)
    (snap,) = snapshot([live.db_path], tmp_path / "snaps", stamp="s2")
    for suffix in ("-wal", "-shm"):
        live.db_path.with_name(live.db_path.name + suffix).write_bytes(b"stale frames")
    restore(snap, live.db_path)
    assert not live.db_path.with_name(live.db_path.name + "-wal").exists()
    assert not live.db_path.with_name(live.db_path.name + "-shm").exists()
    assert integrity_ok(live.db_path)
