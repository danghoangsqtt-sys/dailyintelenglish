"""Create a deterministic-layout, deflated setup ZIP from one edition folder."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Folder containing the app directory and SETUP.txt")
    parser.add_argument("destination", type=Path, help="Output ZIP path")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve()
    app = source / "DailyIntelEnglishStudio"
    if not (app / "DailyIntelEnglishStudio.exe").is_file() or not (app / "_internal").is_dir():
        raise SystemExit("Source folder is not a complete desktop application distribution")
    if not (source / "SETUP.txt").is_file():
        raise SystemExit("Source folder is missing SETUP.txt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())
    with ZipFile(destination) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"Corrupt ZIP member: {bad_member}")
        names = set(archive.namelist())
        if "SETUP.txt" not in names or "DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe" not in names:
            raise RuntimeError("Setup ZIP is missing its setup instructions or executable")


if __name__ == "__main__":
    main()
