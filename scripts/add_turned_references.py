r"""Task 29.1: give Lan and Minh a turned face reference (asset kind `face_turned`) for the gaze toward the other person.

    venv\Scripts\python scripts\add_turned_references.py                      # the data folder of the settings
    DIE_DATA_DIR=data/tmp/smoke28-4b venv\Scripts\python scripts\add_turned_references.py   # a throw-away copy

The app must not be running. The picture is cropped like `face.png` (the library's own crop), stored as
`library/characters/<id>/face_turned.png` and registered as an asset; running it again replaces it. When it runs on the
real data folder the database is copied to `data/backups/` first.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.services.visuals import library_service  # noqa: E402

PICTURES = {
    "Lan": ROOT / "docs" / "operations" / "phase28-characters" / "woman_face_turn.png",
    "Minh": ROOT / "docs" / "operations" / "phase28-characters" / "man_face_turn.png",
}


def main() -> int:
    data_dir = settings.DATA_DIR.resolve()
    real = data_dir == (ROOT / "data").resolve()
    if real:
        backup = ROOT / "data" / "backups" / "app_before_turned_faces_29_1_20261007.db"
        if not backup.exists():
            shutil.copy2(settings.db_path, backup)
            print("backup:", backup)
    connection = sqlite3.connect(settings.db_path)
    for name, picture in PICTURES.items():
        row = connection.execute("SELECT id FROM characters WHERE name = ?", (name,)).fetchone()
        if row is None:
            print(f"skip {name}: not in the library")
            continue
        folder = data_dir / "library" / "characters" / row[0]
        target = folder / "face_turned.png"
        library_service._face_crop_sync(picture, target)
        stored = str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target)
        connection.execute("DELETE FROM character_assets WHERE character_id = ? AND kind = 'face_turned'", (row[0],))
        connection.execute(
            "INSERT INTO character_assets (id, character_id, kind, path, approved, created_at) VALUES (?, ?, 'face_turned', ?, 0, ?)",
            (str(uuid.uuid4()), row[0], stored, datetime.now(timezone.utc).isoformat()))
        print(f"{name}: {stored}")
    connection.commit()
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
