"""Install/verify skills-lock.json entries under .agents/skills/ (gitignored)."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Extra recipe skills not yet in lock — install then hash into lock when --update-lock.
EXTRA: dict[str, dict[str, str]] = {
    "caveman-commit": {
        "source": "juliusbrussee/caveman",
        "skillPath": "skills/caveman-commit/SKILL.md",
    },
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_available() -> bool:
    return shutil.which("git") is not None


def _clone_skill(source: str, skill_path: str, dest_dir: Path) -> Path | None:
    """Sparse-fetch one skill file tree into dest_dir; return SKILL.md path."""
    if not _git_available():
        print("FAIL: git not on PATH", file=sys.stderr)
        return None
    url = f"https://github.com/{source}.git"
    sparse = Path(skill_path).parent.as_posix()
    with tempfile.TemporaryDirectory(prefix="skills-lock-") as tmp:
        repo = Path(tmp) / "repo"
        steps = [
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "--no-checkout",
                url,
                str(repo),
            ],
            ["git", "-C", str(repo), "sparse-checkout", "set", "--cone", sparse],
            ["git", "-C", str(repo), "checkout"],
        ]
        for cmd in steps:
            proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if proc.returncode != 0:
                print(proc.stderr or proc.stdout, file=sys.stderr)
                print(f"FAIL: {' '.join(cmd)}", file=sys.stderr)
                return None
        src_skill = repo / skill_path
        if not src_skill.is_file():
            print(f"FAIL: {skill_path} not in {source}", file=sys.stderr)
            return None
        dest_dir.mkdir(parents=True, exist_ok=True)
        src_folder = src_skill.parent
        for item in src_folder.iterdir():
            target = dest_dir / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
        out = dest_dir / "SKILL.md"
        return out if out.is_file() else None


def load_lock(root: Path) -> dict:
    path = root / "skills-lock.json"
    if not path.is_file():
        return {"version": 1, "skills": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_lock(root: Path, data: dict) -> None:
    path = root / "skills-lock.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ensure_skills(root: Path, *, update_lock: bool = False) -> int:
    lock = load_lock(root)
    skills = dict(lock.get("skills") or {})
    for name, meta in EXTRA.items():
        if name not in skills:
            skills[name] = {
                "source": meta["source"],
                "sourceType": "github",
                "skillPath": meta["skillPath"],
                "computedHash": "",
            }
    agents = root / ".agents" / "skills"
    agents.mkdir(parents=True, exist_ok=True)
    missing = 0
    for name, meta in sorted(skills.items()):
        dest = agents / name
        skill_md = dest / "SKILL.md"
        source = str(meta.get("source") or "")
        skill_path = str(meta.get("skillPath") or "SKILL.md")
        expected = str(meta.get("computedHash") or "").strip()
        if skill_md.is_file():
            digest = _sha256_file(skill_md)
            if expected and digest != expected:
                print(f"WARN {name}: hash drift (local {digest[:12]}… vs lock)")
            else:
                print(f"OK   {name}")
            if update_lock:
                meta["computedHash"] = digest
            continue
        print(f"INSTALL {name} from {source}…")
        out = _clone_skill(source, skill_path, dest)
        if out is None:
            missing += 1
            continue
        digest = _sha256_file(out)
        meta["computedHash"] = digest
        print(f"OK   {name} installed ({digest[:12]}…)")
    lock["skills"] = skills
    if update_lock:
        save_lock(root, lock)
        print("OK   skills-lock.json updated")
    if missing:
        print(f"FAIL: {missing} skill(s) not installed", file=sys.stderr)
        return 1
    print(f"OK   {len(skills)} skills present under .agents/skills/")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument(
        "--update-lock",
        action="store_true",
        help="Write computed hashes (and EXTRA skills) into skills-lock.json",
    )
    args = p.parse_args(argv)
    return ensure_skills(args.root.resolve(), update_lock=args.update_lock)


if __name__ == "__main__":
    raise SystemExit(main())
