"""Task 28.4a: regenerate the 55 built-in scene plates in the Phase 28 look. Run with the project venv; the image
worker runs in venv-image on the GPU (the app must not be running: it needs the GPU lease).

    venv\\Scripts\\python scripts\\regenerate_scene_plates.py            # all scenes, resumable
    venv\\Scripts\\python scripts\\regenerate_scene_plates.py --only builtin-bookshop builtin-cafe
    venv\\Scripts\\python scripts\\regenerate_scene_plates.py --sheets-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.visuals import recipes  # noqa: E402
from app.services.visuals.engine import WorkerImageEngine  # noqa: E402

DB = ROOT / "data" / "app.db"
BACKUP_PLATES = ROOT / "data" / "tmp" / "plates-cel-anime-backup"
WORK = ROOT / "data" / "tmp" / "plates-new"
SHEETS = ROOT / "docs" / "operations" / "phase28-scene-plates"
PEOPLE_FRACTION = 0.05  # a plate must be empty; above this the cut-out sees a person
MAX_RETRIES = 2
PER_SHEET = 12


def load_scenes() -> list[dict]:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    rows = [dict(row) for row in connection.execute(
        "select id, name, category, place, staging, time_of_day, seed, preview_path from scenes order by category, name")]
    connection.close()
    return rows


def plate_path(scene: dict) -> Path:
    return ROOT / "data" / "library" / "scenes" / scene["id"] / "preview.png"


def update_scene(scene: dict, seed: int) -> None:
    connection = sqlite3.connect(DB)
    connection.execute("update scenes set preview_path = ?, seed = ?, updated_at = ? where id = ?",
                       (str(plate_path(scene).relative_to(ROOT)), seed,
                        datetime.now(timezone.utc).isoformat(), scene["id"]))
    connection.commit()
    connection.close()


async def render_all(only: list[str]) -> None:
    scenes = [s for s in load_scenes() if not only or s["id"] in only]
    WORK.mkdir(parents=True, exist_ok=True)
    BACKUP_PLATES.mkdir(parents=True, exist_ok=True)
    done_file = WORK / "done.json"
    done = json.loads(done_file.read_text(encoding="utf-8")) if done_file.exists() and not only else {}
    flagged: dict[str, float] = {}
    started_all = time.monotonic()
    engine = WorkerImageEngine()
    async with engine.session("text2img", ip="none", consumer="visuals_scene_plates") as session:
        for index, scene in enumerate(scenes, 1):
            if scene["id"] in done:
                continue
            old = plate_path(scene)
            backup = BACKUP_PLATES / f"{scene['id']}.png"
            if old.exists() and not backup.exists():
                shutil.copy2(old, backup)
            seed, fraction = int(scene["seed"] or random.randint(1, 2**31 - 1)), 1.0
            for attempt in range(MAX_RETRIES + 1):
                out = WORK / f"{scene['id']}.png"
                started = time.monotonic()
                await session.request({
                    "command": "generate", "prompt": recipes.scene_preview_prompt(scene),
                    "negative_prompt": recipes.PLATE_NEGATIVE, "seed": seed, "width": 1344, "height": 768,
                    "steps": 30, "guidance_scale": 6.0, "output_path": str(out)})
                cut = WORK / f"{scene['id']}_cut.png"
                response = await session.request({"command": "remove_background", "input_path": str(out),
                                                  "output_path": str(cut)})
                fraction = float(response.get("foreground_fraction", 0.0))
                cut.unlink(missing_ok=True)
                print(json.dumps({"n": index, "scene": scene["id"], "seed": seed, "attempt": attempt,
                                  "people": round(fraction, 3), "sec": round(time.monotonic() - started, 1)}),
                      flush=True)
                if fraction <= PEOPLE_FRACTION:
                    break
                seed = random.randint(1, 2**31 - 1)
            if fraction > PEOPLE_FRACTION:
                flagged[scene["id"]] = round(fraction, 3)
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out, old)
            update_scene(scene, seed)
            done[scene["id"]] = seed
            if not only:
                done_file.write_text(json.dumps(done), encoding="utf-8")
    (WORK / "flagged.json").write_text(json.dumps(flagged, indent=1), encoding="utf-8")
    print(json.dumps({"rendered": len(done), "flagged": flagged,
                      "total_sec": round(time.monotonic() - started_all, 1), "model": settings.IMAGE_BASE_REPO}),
          flush=True)


def sheets() -> None:
    SHEETS.mkdir(parents=True, exist_ok=True)
    scenes = load_scenes()
    width, height = 448, 252
    for number, start in enumerate(range(0, len(scenes), PER_SHEET), 1):
        chunk = scenes[start:start + PER_SHEET]
        sheet = Image.new("RGB", (width * 3, (height + 18) * 4), "white")
        draw = ImageDraw.Draw(sheet)
        for position, scene in enumerate(chunk):
            x, y = (position % 3) * width, (position // 3) * (height + 18)
            sheet.paste(Image.open(plate_path(scene)).convert("RGB").resize((width, height)), (x, y + 18))
            draw.text((x + 4, y + 3), f"{scene['name']} ({scene['category']}, {scene['time_of_day']})", fill="black")
        sheet.save(SHEETS / f"plates_{number}.png")
    print(f"sheets: {len(range(0, len(scenes), PER_SHEET))}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--sheets-only", action="store_true")
    args = parser.parse_args()
    if not args.sheets_only:
        asyncio.run(render_all(args.only))
    sheets()
    return 0


if __name__ == "__main__":
    sys.exit(main())
