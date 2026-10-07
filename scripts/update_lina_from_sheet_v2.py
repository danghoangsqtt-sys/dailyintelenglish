r"""Phase 31: give Lina the owner's new character sheet (docs/operations/phase31-characters/lina_sheet_v2.jpg), in place.

    venv\Scripts\python scripts\update_lina_from_sheet_v2.py --preview     # only writes the cut pictures to data\tmp
    venv\Scripts\python scripts\update_lina_from_sheet_v2.py --apply

The app must not be running. The character keeps its id, so projects, casts and her library pictures stay. The pictures of her
reference (the face, the face turned toward the other person, the calm / smile / surprised portraits, the full-body view and the
candidate) are replaced by cuts of the new sheet. The old folder is copied to `data/backups/lina_v1_20261008/` first and the database
to `data/backups/`. The library pictures the owner imported (gaze tag "imported") belong to the owner's own Lina, so they are signed
again with the new face; pictures that were drawn by the app are not touched and show as stale until she is redrawn.
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import aiosqlite  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.transactions import write_transaction  # noqa: E402
from app.services.visuals import shot_library_service as lib  # noqa: E402

SHEET = ROOT / "docs" / "operations" / "phase31-characters" / "lina_sheet_v2.jpg"
WORK = ROOT / "data" / "tmp" / "lina-v2"
BACKUP_DB = ROOT / "data" / "backups" / "app_before_lina_v2_20261008.db"
BACKUP_FOLDER = ROOT / "data" / "backups" / "lina_v1_20261008"

# Pixels of the 1536 x 1024 sheet: (panel, middle of the eyes, chin) of the two big face views; the smile and surprised
# panels of the expression grid; the front full-body panel.
FRONT = ((445, 45, 640, 545), (541, 238), 352)
ANGLE = ((815, 45, 995, 545), (876, 230), 352)
SMILE = (1133, 72, 1262, 290)
SURPRISED = (1003, 322, 1130, 543)
BODY = (5, 66, 152, 760)


def face_crop(sheet: Image.Image, panel: tuple, eyes: tuple, chin_y: float, size: int = 512) -> Image.Image:
    """A square face crop (eyes at 0.5, chin at 0.9 of the height) on the panel's own plain background."""
    part = sheet.crop(panel)
    background = part.getpixel((7, 7))
    eye_x, eye_y = eyes
    side = round((chin_y - eye_y) / 0.4)
    canvas = Image.new("RGB", (side, side), background)
    canvas.paste(part, (panel[0] - round(eye_x - side / 2), panel[1] - round(eye_y - side / 2)))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def panel_square(sheet: Image.Image, box: tuple, size: int = 512) -> Image.Image:
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    side = max(width, height)
    canvas = Image.new("RGB", (side, side), sheet.crop(box).getpixel((3, 3)))
    canvas.paste(sheet.crop(box), ((side - width) // 2, 0))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def cut() -> dict[str, Path]:
    WORK.mkdir(parents=True, exist_ok=True)
    with Image.open(SHEET) as opened:
        sheet = opened.convert("RGB")
    front = face_crop(sheet, *FRONT)
    turned = ImageOps.mirror(face_crop(sheet, *ANGLE))  # the sheet turns toward the viewer's left; the library wants "looks right"
    body = sheet.crop(BODY)
    body = body.resize((round(body.width * 1216 / body.height), 1216), Image.Resampling.LANCZOS)
    pictures = {"face_front": front, "face_turned": turned, "portrait_smile": panel_square(sheet, SMILE),
                "portrait_surprised": panel_square(sheet, SURPRISED), "full_body": body}
    paths = {}
    for key, picture in pictures.items():
        paths[key] = WORK / f"{key}.png"
        picture.save(paths[key])
    return paths


async def apply() -> None:
    paths = cut()
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    try:
        row = await (await db.execute("SELECT id FROM characters WHERE name = 'Lina'")).fetchone()
        if row is None:
            raise SystemExit("Lina is not in the library")
        character_id = row["id"]
        folder = settings.DATA_DIR / "library" / "characters" / character_id
        BACKUP_DB.parent.mkdir(parents=True, exist_ok=True)
        if not BACKUP_DB.exists():
            shutil.copy2(settings.db_path, BACKUP_DB)
        if not BACKUP_FOLDER.exists():
            shutil.copytree(folder, BACKUP_FOLDER)
        replacements = {
            folder / "face.png": paths["face_front"], folder / "candidates" / "candidate_0.png": paths["face_front"],
            folder / "face_turned.png": paths["face_turned"], folder / "sheet" / "portrait_calm.png": paths["face_front"],
            folder / "sheet" / "portrait_smile.png": paths["portrait_smile"],
            folder / "sheet" / "portrait_surprised.png": paths["portrait_surprised"],
            folder / "sheet" / "full_body.png": paths["full_body"],
        }
        for target, source in replacements.items():
            shutil.copyfile(source, target)
        (folder / "face_turned_flipped.png").unlink(missing_ok=True)  # the mirrored cache is made again when needed
        async with write_transaction(db):
            before = await db.execute("SELECT id, character_ids_json FROM shot_library WHERE gaze = 'imported'")
            owner_pictures = [dict(r) for r in await before.fetchall()]
            for picture in owner_pictures:
                import json
                ids = json.loads(picture["character_ids_json"])
                if character_id not in ids:
                    continue
                signature = await lib.face_signature(db, ids)
                await db.execute("UPDATE shot_library SET face_signature = ?, stale = 0 WHERE id = ?", (signature, picture["id"]))
        print(f"Lina updated; {len([p for p in owner_pictures if character_id in p['character_ids_json']])} of the owner's pictures signed again")
        print("old folder:", BACKUP_FOLDER)
    finally:
        await db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preview", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.preview:
        print({key: str(path) for key, path in cut().items()})
    else:
        asyncio.run(apply())
    return 0


if __name__ == "__main__":
    sys.exit(main())
