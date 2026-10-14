"""Phase 44 (D123): back up the database and zip the old two-person shot pictures before they are removed.

    python scripts/archive_old_shots.py            # list what would be archived (dry run)
    python scripts/archive_old_shots.py --apply    # back up the DB, write the zip, then delete the archived pictures

The zip keeps the original relative paths (data/visuals/<project>/shots/..., data/library/shots/...), so a picture can be
restored by unzipping at the project root. Rendered videos are never touched.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.core.config import settings  # noqa: E402


def shot_files(data_dir: Path) -> list[Path]:
    """Every picture of the old shot features: each project's `shots/` folder and the two-person Shot Library."""
    files: list[Path] = []
    visuals = data_dir / "visuals"
    if visuals.is_dir():
        for project in sorted(visuals.iterdir()):
            if (project / "shots").is_dir():
                files.extend(sorted(path for path in (project / "shots").rglob("*") if path.is_file()))
    library = data_dir / "library" / "shots"
    if library.is_dir():
        files.extend(sorted(path for path in library.rglob("*") if path.is_file()))
    return files


def archive(data_dir: Path, db_path: Path, backups: Path, apply: bool) -> dict:
    files = shot_files(data_dir)
    size = sum(path.stat().st_size for path in files)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    result = {"files": len(files), "bytes": size, "zip": None, "db_backup": None}
    if not apply:
        return result
    backups.mkdir(parents=True, exist_ok=True)
    db_backup = backups / f"app-before-migration-026-{stamp}.db"
    with sqlite3.connect(db_path) as source, sqlite3.connect(db_backup) as target:
        source.backup(target)  # a consistent copy even while the app runs
    result["db_backup"] = str(db_backup)
    if files:
        zip_path = backups / f"phase44-shots-{stamp}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as bundle:  # PNGs are already compressed
            for path in files:
                bundle.write(path, path.relative_to(data_dir.parent).as_posix())
        with zipfile.ZipFile(zip_path) as bundle:  # verify before deleting anything
            if bundle.testzip() is not None or len(bundle.namelist()) != len(files):
                raise RuntimeError(f"the archive {zip_path} failed its check; nothing was deleted")
        result["zip"] = str(zip_path)
        visuals = data_dir / "visuals"
        for project in visuals.iterdir() if visuals.is_dir() else []:
            shutil.rmtree(project / "shots", ignore_errors=True)
        shutil.rmtree(data_dir / "library" / "shots", ignore_errors=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="back up, archive and delete (default: dry run)")
    args = parser.parse_args()
    data_dir = Path(settings.DATA_DIR)
    result = archive(data_dir, Path(settings.db_path), data_dir / "backups", args.apply)
    mode = "archived and removed" if args.apply else "would archive (dry run)"
    print(f"{mode}: {result['files']} pictures, {result['bytes'] / 1e6:.1f} MB")
    if result["db_backup"]:
        print(f"database backup: {result['db_backup']}")
    if result["zip"]:
        print(f"pictures: {result['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
