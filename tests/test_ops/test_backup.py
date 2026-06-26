from pathlib import Path

from trendalgo.ops.backup import create_backup, restore_backup


def test_backup_roundtrip(tmp_path: Path) -> None:
    data = tmp_path / "data"
    config = tmp_path / "config"
    data.mkdir()
    config.mkdir()
    (data / "portfolio.db").write_bytes(b"sqlite")
    (config / "bot" / "dryrun.example.json").parent.mkdir(parents=True)
    (config / "bot" / "dryrun.example.json").write_text("{}", encoding="utf-8")
    archive = create_backup(data_dir=data, config_dir=config, output_dir=tmp_path / "backups")
    files = restore_backup(archive, dest_root=tmp_path / "restore", dry_run=True)
    assert any("portfolio.db" in f for f in files)
