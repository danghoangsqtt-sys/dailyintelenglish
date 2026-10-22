"""Export or import the library package from the command line (Phase 70, ENH-052).

The same package as Settings -> Data & sync, for large packages carried on a USB stick or a shared drive. Close the app first:
the script opens the database itself.

Usage:
    python scripts/library_package.py export [--out D:/transfer/library.zip] [--data-dir DIR]
    python scripts/library_package.py import D:/transfer/library.zip [--data-dir DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config import settings  # noqa: E402


async def run(args: argparse.Namespace) -> dict:
    from backend.db import transactions
    from backend.db.database import Database, close_db, init_db
    from backend.library import library_package as package

    if args.data_dir:
        settings.DATA_DIR = Path(args.data_dir).resolve()
    await init_db()  # this machine's schema is brought up to date first
    db = Database.instance().connection
    try:
        if args.command == "export":
            rows = await package.collect_rows(db)
            return await package.write_package(rows, Path(args.out).resolve() if args.out else None)
        source = Path(args.package).resolve()
        async with transactions.write_transaction(db):
            result = await package.merge_rows(db, source)
        result["files"] = await package.extract_files(source)
        return result
    finally:
        await close_db()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", help="the data folder (default: the configured one)")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="write a library package")
    export.add_argument("--out", help="where to write the .zip (default: data/exports/library-<time>.zip)")
    load = commands.add_parser("import", help="merge a library package into this machine")
    load.add_argument("package", help="the .zip to import")
    args = parser.parse_args(argv)
    from backend.library.library_package import PackageError

    try:
        result = asyncio.run(run(args))
    except PackageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
