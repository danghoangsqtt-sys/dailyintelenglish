"""Clean the workspace of temporary and leftover files (Phase 70, ENH-052).

Dry-run by default: lists what would go and how big it is. `--apply` deletes it. Never touches the database, the libraries
(characters, activities, scenes, music), the models, the virtual environments or the newest app backup.

What goes:
- `data/tmp/*` (build stages, upgrade rehearsals, test copies) -- except a folder that is a registered git worktree
- older app backups `data/backups/desktop-*` (the newest is kept) and the old media backups `vertical-motion-*`, `youtube-dialogue-*`
- media of projects that no longer exist (`data/audio|video|thumbnails|visuals|tts_cache|avatars|explainer/<id>`)
- `renderer/public/remotion-render` (render staging), `build` (PyInstaller work folder), `dist/*.next-*`, `demo_output`,
  `debug.log`, `data/exports/incoming`

Usage:
    python scripts/cleanup_workspace.py            # dry-run
    python scripts/cleanup_workspace.py --apply    # delete
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_MEDIA = ("audio", "video", "thumbnails", "visuals", "tts_cache", "avatars", "explainer")
OLD_BACKUPS = ("vertical-motion-", "youtube-dialogue-")


def size_of(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for folder, _dirs, files in os.walk(path, onerror=lambda _error: None):
        for name in files:
            try:
                total += (Path(folder) / name).stat().st_size
            except OSError:
                pass
    return total


def project_ids(data: Path) -> set[str] | None:
    database = data / "app.db"
    if not database.is_file():
        return None
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        return {row[0] for row in connection.execute("SELECT id FROM projects")}
    finally:
        connection.close()


def targets(root: Path = ROOT) -> list[tuple[str, Path]]:
    data = root / "data"
    found: list[tuple[str, Path]] = []
    tmp = data / "tmp"
    if tmp.is_dir():
        for path in sorted(tmp.iterdir()):
            if (path / ".git").is_file():  # a registered worktree: remove it with `git worktree remove`
                continue
            found.append(("temporary", path))
    backups = data / "backups"
    if backups.is_dir():
        desktop = sorted((path for path in backups.glob("desktop-*") if path.is_dir()), key=lambda path: path.name)
        found += [("older app backup", path) for path in desktop[:-1]]
        found += [("old media backup", path) for path in sorted(backups.iterdir()) if path.name.startswith(OLD_BACKUPS)]
    ids = project_ids(data)
    if ids is not None:
        for category in PROJECT_MEDIA:
            folder = data / category
            if folder.is_dir():
                found += [("deleted project media", path) for path in sorted(folder.iterdir())
                          if path.is_dir() and _looks_like_id(path.name) and path.name not in ids]
    for label, path in (("render staging", root / "renderer" / "public" / "remotion-render"), ("build work folder", root / "build"),
                        ("demo output", root / "demo_output"), ("stray log", root / "debug.log"),
                        ("unfinished upload", data / "exports" / "incoming")):
        if path.exists():
            found.append((label, path))
    dist = root / "dist"
    if dist.is_dir():
        found += [("leftover app copy", path) for path in sorted(dist.glob("*.next-*"))]
    return found


def _looks_like_id(name: str) -> bool:
    return len(name) == 36 and name.count("-") == 4


def _force_writable(function, path, _info):
    os.chmod(path, stat.S_IWRITE)
    function(path)


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, onerror=_force_writable)
    else:
        path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="delete (default: only list)")
    args = parser.parse_args(argv)
    total = 0
    failed = []
    for label, path in targets():
        size = size_of(path)
        total += size
        print(f"{size / 1e6:10.1f} MB  {label:22}  {path.relative_to(ROOT)}")
        if args.apply:
            try:
                remove(path)
            except OSError as error:
                failed.append(f"{path}: {error}")
    print(f"{total / 1e9:.2f} GB {'deleted' if args.apply else 'would be deleted (dry run; pass --apply)'}")
    for line in failed:
        print(f"could not delete {line}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
