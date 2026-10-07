r"""Phase 31: replace Lan and Minh with Alex and Lina, the owner's own characters (Russian), from the pictures the owner made.

    venv\Scripts\python scripts\replace_with_alex_lina.py --dry-run
    venv\Scripts\python scripts\replace_with_alex_lina.py --apply

The app must not be running. The owner's character sheets and poses are in `docs/operations/phase31-characters/`. From them the
script cuts the face references (front, and a face turned about 45 degrees for the gaze toward the other person, mirrored so it
looks right), the smile and surprised portraits and the full-body view, creates the two characters through the library's own
service functions in one `write_transaction` (every rule of the library applies), moves the cast of every project from the old
character of the same gender to the new one, and deletes the old characters (their library pictures go with them). The old
character folders are copied to `data/tmp/characters-old-backup-31/` and the database to `data/backups/` first.
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
from app.models.visuals import CharacterInput  # noqa: E402
from app.services.visuals import library_service as library  # noqa: E402

REFS = ROOT / "docs" / "operations" / "phase31-characters"
WORK = ROOT / "data" / "tmp" / "new-characters" / "prepared"
BACKUP_DB = ROOT / "data" / "backups" / f"app_before_alex_lina_31_20261007_{settings.DATA_DIR.resolve().name}.db"
BACKUP_FOLDERS = ROOT / "data" / "tmp" / "characters-old-backup-31"
SEED = 31

# Where the pictures sit in the owner's sheets (pixels of the 1448 x 1086 sheets): the face panel, the middle of the eyes and the
# chin (the face crop puts the eyes at half and the chin at 0.9 of the square), and the smile / surprised panels.
SPEC = {
    "Lina": {
        "form": dict(name="Lina", gender="female", age_group="young", ethnicity="Russian", role="English teacher",
                     hair="long chocolate brown hair", eyes="brown eyes", extra="fair porcelain skin, curtain bangs",
                     top_color="white", top_item="mini dress", bottom_color="white", bottom_item="mini dress"),
        "sheet": "lina_sheet.jpg", "pose": "lina_pose1.jpg",
        "front": ((420, 70, 603, 512), (501, 224), 345), "turned": ((770, 70, 938, 512), (826, 222), 340),
        "smile": (1068, 72, 1190, 272), "surprised": (947, 305, 1066, 510),
    },
    "Alex": {
        "form": dict(name="Alex", gender="male", age_group="young", ethnicity="Russian", role="university student",
                     hair="short swept-back brown hair", eyes="brown eyes", extra="caramel blond highlights, clean-shaven",
                     top_color="navy blue", top_item="suit jacket", bottom_color="navy blue", bottom_item="suit trousers"),
        "sheet": "alex_sheet.jpg", "pose": "alex_pose3.jpg",
        "front": ((507, 42, 695, 298), (588, 158), 235), "turned": ((888, 42, 1073, 298), (972, 150), 232),
        "smile": (649, 372, 790, 557), "surprised": (507, 585, 645, 775),
    },
}


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


def prepare(name: str) -> dict[str, Path]:
    spec = SPEC[name]
    folder = WORK / name.lower()
    folder.mkdir(parents=True, exist_ok=True)
    with Image.open(REFS / spec["sheet"]) as opened:
        sheet = opened.convert("RGB")
    front = face_crop(sheet, *spec["front"])
    turned = ImageOps.mirror(face_crop(sheet, *spec["turned"]))  # the sheet turns toward the viewer's left; the library wants "looks right"
    pictures = {
        "face_front": front, "face_turned": turned, "portrait_smile": panel_square(sheet, spec["smile"]),
        "portrait_surprised": panel_square(sheet, spec["surprised"]),
    }
    paths = {}
    for key, picture in pictures.items():
        paths[key] = folder / f"{key}.png"
        picture.save(paths[key])
    with Image.open(REFS / spec["pose"]) as pose:
        paths["full_body"] = folder / "full_body.png"
        pose.convert("RGB").save(paths["full_body"])
    return paths


def relative(path: Path) -> Path:
    return path.resolve().relative_to(ROOT)


async def run(apply: bool) -> None:
    prepared = {name: prepare(name) for name in SPEC}
    for name, spec in SPEC.items():
        CharacterInput(**spec["form"])  # raises on a form the library would refuse
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        old = [dict(row) for row in await (await db.execute("SELECT id, name, gender, status FROM characters")).fetchall()]
        casts = [dict(row) for row in await (await db.execute(
            "SELECT project_id, speaker_index, character_id FROM project_cast")).fetchall()]
        shots = (await (await db.execute("SELECT COUNT(*) FROM shot_library")).fetchone())[0]
        print(f"old characters: {[(c['name'], c['gender'], c['status']) for c in old]}")
        print(f"cast rows to move: {len(casts)}, library pictures that go with the old characters: {shots}")
        print("prepared pictures in", WORK)
        if not apply:
            print("dry run: nothing written. New characters:", ", ".join(SPEC))
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
                for name, spec in SPEC.items():
                    paths = prepared[name]
                    view = await library.create_character(db, CharacterInput(**spec["form"]))
                    character_id = view["id"]
                    created[name] = character_id
                    folder = settings.DATA_DIR / "library" / "characters" / character_id
                    (folder / "candidates").mkdir(parents=True, exist_ok=True)
                    (folder / "sheet").mkdir(parents=True, exist_ok=True)
                    candidate = folder / "candidates" / "candidate_0.png"
                    shutil.copy2(paths["face_front"], candidate)
                    asset = await library.add_asset(db, character_id, "candidate", relative(candidate), SEED)
                    await library.pick_reference(db, character_id, asset["id"])
                    shutil.copy2(paths["face_front"], folder / "face.png")  # the cut face itself, not a second crop of it
                    turned = folder / "face_turned.png"
                    shutil.copy2(paths["face_turned"], turned)
                    await library.add_asset(db, character_id, "face_turned", relative(turned), SEED)
                    for kind, source in (("full_body", paths["full_body"]), ("portrait_calm", paths["face_front"]),
                                         ("portrait_smile", paths["portrait_smile"]),
                                         ("portrait_surprised", paths["portrait_surprised"])):
                        target = folder / "sheet" / f"{kind}.png"
                        shutil.copy2(source, target)
                        sheet_asset = await library.add_asset(db, character_id, kind, relative(target), SEED)
                        await library.approve_asset(db, character_id, sheet_asset["id"], True)
                    await library.lock_character(db, character_id)
                gender_of = {name: SPEC[name]["form"]["gender"] for name in SPEC}
                new_by_gender = {gender_of[name]: created[name] for name in SPEC}
                for character in old:
                    await db.execute("UPDATE project_cast SET character_id = ? WHERE character_id = ?",
                                     (new_by_gender[character["gender"]], character["id"]))
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
