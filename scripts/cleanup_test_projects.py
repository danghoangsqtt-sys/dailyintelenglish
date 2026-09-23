"""Delete leaked API-test fixture projects from a database (BUG-023, Task 16.3).

Every `client` fixture in the test suite is supposed to isolate its own tmp
`DATA_DIR`, but a bug in the `*_browser.py` Playwright fixtures (fixed by this same
task) let a handful of full single-process test runs silently write real project
rows into the real database instead. This tool finds and removes them.

Usage:
    python scripts/cleanup_test_projects.py                      # dry-run (default)
    python scripts/cleanup_test_projects.py --apply               # back up, then delete
    python scripts/cleanup_test_projects.py --db PATH --data-dir DIR [--apply]

Dry-run (the default -- no `--apply` needed) only reads: prints each of the 4 known
fixture project names, its count, and the matching ids. Nothing is written.

`--apply` first copies the target db file to
`<data-dir>/backups/app-before-cleanup-<UTC timestamp>.db`, then deletes only
projects whose `name` is an **exact** match (never `LIKE`, never a pattern) of one
of the 4 known fixture names, one at a time, through the same service-layer path
the API's own `DELETE /api/projects/{id}` route uses
(`project_service.delete_project` inside a write transaction, followed by
`project_service.cleanup_project_artifacts`) -- so cascaded DB rows (foreign keys)
and the project's per-project directories are removed too, never left orphaned by
a raw `DELETE FROM projects`.

`--db`/`--data-dir` default to the real, configured database and data directory
(`app.core.config.settings`), so this script's own tests always pass them
explicitly to target a tmp copy instead.

Invariant 26 (Phase 16 plan): only the PM runs `--apply` against the real database,
after a backup and after the owner has seen the dry-run output. The Coder never
passes `--apply` here against anything but a tmp fixture db.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiosqlite  # noqa: E402

FIXTURE_PROJECT_NAMES = (
    "Learning API Test Episode",
    "YouTube API Test Episode",
    "Export API Test Episode",
    "Script API Test Episode",
)


async def find_matches(db: aiosqlite.Connection) -> dict[str, list[str]]:
    """Exact-name matches only (never `LIKE`) for each of the 4 known fixture names."""
    matches: dict[str, list[str]] = {}
    for name in FIXTURE_PROJECT_NAMES:
        cursor = await db.execute("SELECT id FROM projects WHERE name = ?", (name,))
        rows = await cursor.fetchall()
        matches[name] = [row[0] for row in rows]
    return matches


def format_report(matches: dict[str, list[str]]) -> str:
    lines = []
    total = 0
    for name, ids in matches.items():
        lines.append(f"{name}: {len(ids)}")
        lines.extend(f"  {project_id}" for project_id in ids)
        total += len(ids)
    lines.append(f"total: {total}")
    return "\n".join(lines)


def backup_path_for(data_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return data_dir / "backups" / f"app-before-cleanup-{timestamp}.db"


async def apply_deletions(db_path: Path, data_dir: Path, matches: dict[str, list[str]]) -> Path:
    """Back up `db_path`, then delete every matched project via the same
    service-layer path the API's own delete route uses. Returns the backup path."""
    from app.core.config import settings
    from app.db import transactions
    from app.services import project_service

    backup_path = backup_path_for(data_dir)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup_path)

    settings.DATA_DIR = data_dir  # cleanup_project_artifacts reads this to find per-project dirs

    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        for ids in matches.values():
            for project_id in ids:
                async with transactions.write_transaction(db):
                    await project_service.delete_project(db, project_id, commit=False)
                await project_service.cleanup_project_artifacts(project_id)
    finally:
        await db.close()

    return backup_path


async def run(db_path: Path, data_dir: Path, apply: bool) -> str:
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    try:
        matches = await find_matches(db)
    finally:
        await db.close()

    output = [format_report(matches)]

    if apply:
        backup_path = await apply_deletions(db_path, data_dir, matches)
        output.append(f"backup written to {backup_path}")
        output.append("apply complete")
    else:
        output.append("dry run -- nothing written (pass --apply to delete)")

    return "\n".join(output)


def _default_db_path() -> Path:
    from app.core.config import settings

    return settings.db_path


def _default_data_dir() -> Path:
    from app.core.config import settings

    return settings.DATA_DIR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--db", type=Path, default=None, help="Path to the target app.db (default: the real, configured one)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="DATA_DIR the target db belongs to, for per-project directory cleanup and the "
        "backup location (default: the real, configured one)",
    )
    parser.add_argument(
        "--apply", action="store_true", help="Actually back up and delete (default is dry-run, writes nothing)"
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    db_path = args.db if args.db is not None else _default_db_path()
    data_dir = args.data_dir if args.data_dir is not None else _default_data_dir()
    print(asyncio.run(run(db_path, data_dir, args.apply)))


if __name__ == "__main__":
    main()
