"""Task 28.4b helper: a throw-away copy of the data folder whose stored paths point at the copy, so an app instance
started with DIE_DATA_DIR=<copy> can run the real pipelines without touching the real data.

    venv\\Scripts\\python scripts\\make_smoke_copy.py data\\tmp\\smoke28-4b
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(target_arg: str) -> None:
    target = (ROOT / target_arg).resolve()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    shutil.copy2(ROOT / "data" / "app.db", target / "app.db")
    shutil.copytree(ROOT / "data" / "library", target / "library")
    prefix_old = str(Path("data") / "library")        # stored paths are relative to the project root
    prefix_new = str(Path(target_arg) / "library")
    visuals_old, visuals_new = str(Path("data") / "visuals"), str(Path(target_arg) / "visuals")
    db = sqlite3.connect(target / "app.db")
    counts = {
        "character_assets": db.execute("UPDATE character_assets SET path = replace(path, ?, ?)",
                                       (prefix_old, prefix_new)).rowcount,
        "scenes": db.execute("UPDATE scenes SET preview_path = replace(preview_path, ?, ?) "
                             "WHERE preview_path IS NOT NULL", (prefix_old, prefix_new)).rowcount,
        "shots_raw": db.execute("UPDATE project_shots SET raw_path = replace(raw_path, ?, ?) "
                                "WHERE raw_path IS NOT NULL", (visuals_old, visuals_new)).rowcount,
        "shots_final": db.execute("UPDATE project_shots SET final_path = replace(final_path, ?, ?) "
                                  "WHERE final_path IS NOT NULL", (visuals_old, visuals_new)).rowcount,
    }
    db.commit()
    sample = db.execute("SELECT path FROM character_assets LIMIT 1").fetchone()[0]
    db.close()
    print(counts, "| sample:", sample)
    assert "\t" not in sample and prefix_new in sample


if __name__ == "__main__":
    main(sys.argv[1])
