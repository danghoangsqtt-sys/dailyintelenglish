r"""Task 24.3 spike: do the action poses + beat prompts read as the actions? Not shipped.

Real worker pipeline (L1 encode with face + scene plate, L2 ControlNet render with both
adapters; no repair passes), the real locked Lan + Minh faces and the real Cafe plate.

    venv\Scripts\python scripts\spike_beat_poses.py --out <dir>
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.visuals import geometry, recipes  # noqa: E402
from app.services.visuals.engine import WorkerImageEngine  # noqa: E402

SIZE = (1344, 768)
SINGLES = [
    ("talk", "talking about remote work", "calm"),
    ("point", "pointing at a city map", "surprised"),
    ("drink", "drinking coffee", "smile"),
    ("phone", "talking on the phone", "worried"),
    ("think", "thinking about the future", "thinking"),
    ("wave", "waving goodbye", "laugh"),
    ("work", "typing on a laptop", "serious"),
]
DUOS = [("duo_close", "drinking coffee together", "smile"), ("duo_wide", "looking at a laptop screen", "thinking")]


def characters() -> tuple[list[dict], list[str]]:
    db = sqlite3.connect(ROOT / "data" / "app.db")
    db.row_factory = sqlite3.Row
    people, faces = [], []
    for name in ("Lan", "Minh"):
        row = dict(db.execute("SELECT * FROM characters WHERE name = ?", (name,)).fetchone())
        people.append(row)
        faces.append(str(ROOT / db.execute(
            "SELECT path FROM character_assets WHERE character_id = ? AND kind = 'face'", (row["id"],)).fetchone()[0]))
    return people, faces


async def run(out: Path) -> None:
    people, faces = characters()
    scene = {"place": "a cozy Vietnamese street cafe", "staging": "seated"}
    plate = str(ROOT / "data" / "library" / "scenes" / "builtin-cafe" / "preview.png")
    jobs = []
    for category, action, expression in SINGLES:
        assert geometry.action_category(action) == category, (action, category)
        jobs.append({"label": f"single_{category}", "kind": "single", "faces": [faces[0]],
                     "people": geometry.beat_people("single", "seated", SIZE, [category]),
                     "prompt": recipes.beat_single_prompt(people[0], scene, action, expression), "seed": 41})
    for kind, action, expression in DUOS:
        category = geometry.action_category(action)
        jobs.append({"label": f"{kind}_{category}", "kind": kind, "faces": faces,
                     "people": geometry.beat_people(kind, "seated", SIZE, [category, category]),
                     "prompt": recipes.beat_duo_prompt(people[0], people[1], scene, kind, action, expression),
                     "seed": 42})
    engine = WorkerImageEngine()
    async with engine.session("text2img", ip="with_encoder", consumer="spike_beat_encode", scene=True) as session:
        for job in jobs:
            folder = out / job["label"]
            folder.mkdir(parents=True, exist_ok=True)
            job["folder"], job["embeds"] = folder, folder / "embeds.pt"
            payload = {"command": "encode", "output_path": str(job["embeds"]), "guidance_scale": 6.0,
                       "items": [{"prompt": job["prompt"], "negative_prompt": recipes.NEGATIVE}],
                       "ip_adapter_scene_image": plate}
            payload["ip_adapter_image" if len(job["faces"]) == 1 else "ip_adapter_images"] = (
                job["faces"][0] if len(job["faces"]) == 1 else job["faces"])
            response = await session.request(payload)
            print(job["label"], response["item_tokens"][0], job["prompt"][len(recipes.STYLE_CEL_ANIME) + 2:], flush=True)
    async with engine.session("controlnet", encoders=False, ip="layers_only", consumer="spike_beat_render",
                              scene=True) as session:
        for job in jobs:
            folder = job["folder"]
            geometry.draw_people(job["people"], SIZE).save(folder / "pose.png")
            geometry.background_mask(job["people"], SIZE).save(folder / "scene_mask.png")
            payload = {"command": "generate", "embeds_path": str(job["embeds"]), "embeds_index": 0, "seed": job["seed"],
                       "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                       "output_path": str(folder / "raw.png"), "control_image": str(folder / "pose.png"),
                       "controlnet_conditioning_scale": 1.0, "ip_adapter_scale": 0.45,
                       "ip_adapter_scene_mask": str(folder / "scene_mask.png"),
                       "ip_adapter_scene_scale": settings.VISUALS_SCENE_REFERENCE_SCALE}
            if job["kind"] != "single":
                left, right = geometry.half_masks(SIZE)
                left.save(folder / "l.png")
                right.save(folder / "r.png")
                payload["ip_adapter_masks"] = [str(folder / "l.png"), str(folder / "r.png")]
            await session.request(payload)
            print(job["label"], "rendered", flush=True)
    cw, ch, cap = 448, 256, 16
    sheet = Image.new("RGB", (cw * 3, (ch + cap) * 3), "white")
    draw = ImageDraw.Draw(sheet)
    for index, job in enumerate(jobs):
        x, y = (index % 3) * cw, (index // 3) * (ch + cap)
        draw.text((x + 4, y + 2), job["label"], fill="black")
        with Image.open(job["folder"] / "raw.png") as image:
            sheet.paste(image.resize((cw, ch)), (x, y + cap))
    sheet.save(out / "contact.png")
    print("done", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    asyncio.run(run(Path(parser.parse_args().out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
