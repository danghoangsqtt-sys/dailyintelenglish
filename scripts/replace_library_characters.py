"""Task 28.4: replace the two old library characters with Lan and Minh (the Task 28.2 sheets).

    venv\\Scripts\\python scripts\\replace_library_characters.py --dry-run
    venv\\Scripts\\python scripts\\replace_library_characters.py --apply

The app must not be running. It uses the library's own service functions inside one `write_transaction`, so every
rule of the library applies (four approved sheet views and a picked reference before a lock, and so on). The cast of
a project that used an old character is moved to the new character of the same name. The old character folders go to
`data/tmp/characters-old-backup/` and the database is copied to `data/backups/` first.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aiosqlite  # noqa: E402
from PIL import Image  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.transactions import write_transaction  # noqa: E402
from app.models.visuals import CharacterInput  # noqa: E402
from app.services.visuals import library_service as library  # noqa: E402

SHEETS = ROOT / "docs" / "operations" / "phase28-characters"
CAND = ROOT / "data" / "tmp" / "character-sheets"
BACKUP_DB = ROOT / "data" / "backups" / "app_before_new_characters_28_4_20261006.db"
BACKUP_FOLDERS = ROOT / "data" / "tmp" / "characters-old-backup"

NEW = {
    "Lan": {
        "form": dict(name="Lan", gender="female", age_group="young", ethnicity="Vietnamese", role="English teacher",
                     hair="long straight black hair", eyes="dark eyes", top_color="white", top_item="blouse",
                     bottom_color="white", bottom_item="trousers"),
        "seed": 21,
        "candidate": SHEETS / "woman_face_front.png",
        "sheet": {"full_body": SHEETS / "woman_full_front.png", "portrait_calm": SHEETS / "woman_face_front.png",
                  "portrait_smile": SHEETS / "woman_face_smile.png",
                  "portrait_surprised": CAND / "woman_face_surprised_s42.png"},
    },
    "Minh": {
        "form": dict(name="Minh", gender="male", age_group="young", ethnicity="Vietnamese", role="university student",
                     hair="tousled black hair", eyes="dark eyes", top_color="black", top_item="slim-fit shirt",
                     bottom_color="black", bottom_item="slim trousers"),
        "seed": 21,
        "candidate": SHEETS / "man_face_front.png",
        "sheet": {"full_body": SHEETS / "man_full_front.png", "portrait_calm": SHEETS / "man_face_front.png",
                  "portrait_smile": SHEETS / "man_face_smile.png",
                  "portrait_surprised": CAND / "man_face_surprised_s21.png"},
    },
}


def relative(path: Path) -> Path:
    return path.resolve().relative_to(ROOT)


def check_inputs() -> list[str]:
    problems = []
    for name, spec in NEW.items():
        CharacterInput(**spec["form"])  # raises on a form the library would refuse
        for path in (spec["candidate"], *spec["sheet"].values()):
            if not path.is_file():
                problems.append(f"{name}: missing {path}")
            else:
                with Image.open(path) as image:
                    if min(image.size) < 512:
                        problems.append(f"{name}: {path.name} is only {image.size}")
    return problems


async def run(apply: bool) -> None:
    problems = check_inputs()
    if problems:
        raise SystemExit("cannot continue:\n  " + "\n  ".join(problems))
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        old = [dict(row) for row in await (await db.execute("SELECT id, name, status FROM characters")).fetchall()]
        casts = [dict(row) for row in await (await db.execute(
            "SELECT project_id, speaker_index, character_id FROM project_cast")).fetchall()]
        print(f"old characters: {[(c['name'], c['status']) for c in old]}")
        print(f"cast rows to move: {len(casts)}")
        if not apply:
            print("dry run: nothing written. New characters:", ", ".join(NEW))
            return
        BACKUP_DB.parent.mkdir(parents=True, exist_ok=True)
        if not BACKUP_DB.exists():
            shutil.copy2(settings.db_path, BACKUP_DB)
        BACKUP_FOLDERS.mkdir(parents=True, exist_ok=True)
        for character in old:
            folder = settings.DATA_DIR / "library" / "characters" / character["id"]
            if folder.exists() and not (BACKUP_FOLDERS / character["id"]).exists():
                shutil.copytree(folder, BACKUP_FOLDERS / character["id"])
        created: dict[str, str] = {}
        try:
            async with write_transaction(db):
                for name, spec in NEW.items():
                    view = await library.create_character(db, CharacterInput(**spec["form"]))
                    character_id = view["id"]
                    created[name] = character_id
                    folder = settings.DATA_DIR / "library" / "characters" / character_id
                    (folder / "candidates").mkdir(parents=True, exist_ok=True)
                    (folder / "sheet").mkdir(parents=True, exist_ok=True)
                    candidate = folder / "candidates" / "candidate_0.png"
                    shutil.copy2(spec["candidate"], candidate)
                    asset = await library.add_asset(db, character_id, "candidate", relative(candidate), spec["seed"])
                    await library.pick_reference(db, character_id, asset["id"])
                    for kind, source in spec["sheet"].items():
                        target = folder / "sheet" / f"{kind}.png"
                        shutil.copy2(source, target)
                        sheet_asset = await library.add_asset(db, character_id, kind, relative(target), spec["seed"])
                        await library.approve_asset(db, character_id, sheet_asset["id"], True)
                    await library.lock_character(db, character_id)
                for character in old:
                    await db.execute("UPDATE project_cast SET character_id = ? WHERE character_id = ?",
                                     (created[character["name"]], character["id"]))
                    await library.delete_character(db, character["id"], force=False)
        except Exception:
            for character_id in created.values():  # the database rolled back: drop the copied files too
                shutil.rmtree(settings.DATA_DIR / "library" / "characters" / character_id, ignore_errors=True)
            raise
        for character in old:
            await library.remove_character_files(character["id"])
        print("done:", created)
    finally:
        await db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.apply))
    return 0


if __name__ == "__main__":
    sys.exit(main())
