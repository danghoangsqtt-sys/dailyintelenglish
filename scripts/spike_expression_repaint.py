r"""Task 29.3 spike (ENH-020): can an expression variant of a library shot be made by repainting only the face?

    venv\Scripts\python scripts\spike_expression_repaint.py --shot data\library\shots\<id>.png --characters Minh,Lan
    venv\Scripts\python scripts\spike_expression_repaint.py --shot ... --expressions laugh,surprised,worried,serious

The image worker runs in venv-image on the GPU: the app must not be running (it needs the GPU lease). For each face of
the picture (left to right) an elliptical, feathered mask covers the face, the inpaint session repaints it with the
character's face reference and the expression words, and the result is composited back, so the body, the outfit and the
scene stay exactly as they were. A contact sheet (original + one row per expression) and the seconds per variant are written to
docs/operations/phase29-expression-spike.png / .md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.visuals import recipes  # noqa: E402
from app.services.visuals.engine import WorkerImageEngine  # noqa: E402

OUT = ROOT / "docs" / "operations"
WORK = ROOT / "data" / "tmp" / "expression-spike"
FACE_GROW = 1.7  # the mask is the detected face box grown by this much (hair line and chin included)
STRENGTH = 0.55
FACE_SCALE = 0.6


def character_rows(names: list[str]) -> list[dict]:
    connection = sqlite3.connect(settings.db_path)
    connection.row_factory = sqlite3.Row
    rows = []
    for name in names:
        row = connection.execute("SELECT * FROM characters WHERE name = ?", (name,)).fetchone()
        face = connection.execute("SELECT path FROM character_assets WHERE character_id = ? AND kind = 'face'", (row["id"],)).fetchone()
        rows.append({**dict(row), "face_path": face["path"]})
    connection.close()
    return rows


def face_mask(box: list[float], size: tuple[int, int]) -> Image.Image:
    x1, y1, x2, y2 = box[:4]
    cx, cy, half_w, half_h = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2 * FACE_GROW, (y2 - y1) / 2 * FACE_GROW
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((cx - half_w, cy - half_h, cx + half_w, cy + half_h), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(max(4, round(half_w * 0.12))))


async def run(shot: Path, names: list[str], expressions: list[str]) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    people = character_rows(names)
    original = Image.open(shot).convert("RGB")
    size = original.size
    timings, variants = {}, {}
    engine = WorkerImageEngine()
    async with engine.session("inpaint", ip="with_encoder", consumer="expression_spike") as session:
        found = await session.request({"command": "count_faces", "input_path": str(shot), "expected_faces": len(people)})
        boxes = sorted(found["boxes"], key=lambda box: box[0])[:len(people)]
        print(f"faces found: {len(found['boxes'])}, repainting {len(boxes)}")
        for expression in expressions:
            current = original.copy()
            started = time.monotonic()
            for index, box in enumerate(boxes):
                mask = face_mask(box, size)
                mask_path = WORK / f"mask_{index}.png"
                init_path = WORK / f"init_{expression}_{index}.png"
                out_path = WORK / f"out_{expression}_{index}.png"
                mask.save(mask_path)
                current.save(init_path)
                person = people[index]
                prompt = recipes._styled(recipes.compact_phrase(person), "close-up face", recipes.EXPRESSION_WORDS[expression])
                await session.request({
                    "command": "generate", "prompt": prompt, "negative_prompt": recipes.negative_for(person),
                    "seed": 4242 + index, "width": size[0], "height": size[1], "steps": 30, "guidance_scale": 6.0,
                    "output_path": str(out_path), "init_image": str(init_path), "mask_image": str(mask_path),
                    "strength": STRENGTH, "ip_adapter_image": person["face_path"], "ip_adapter_scale": FACE_SCALE,
                })
                repainted = Image.open(out_path).convert("RGB")
                current = Image.composite(repainted, current, mask)
            timings[expression] = round(time.monotonic() - started, 1)
            variants[expression] = current
            current.save(WORK / f"variant_{expression}.png")
            print(f"{expression}: {timings[expression]} s")
    cell_w, cell_h = 640, round(640 * size[1] / size[0])
    sheet = Image.new("RGB", (cell_w * 3, (cell_h + 16) * ((len(variants) + 1 + 2) // 3)), "white")
    draw = ImageDraw.Draw(sheet)
    for number, (label, picture) in enumerate([("original", original), *variants.items()]):
        x, y = (number % 3) * cell_w, (number // 3) * (cell_h + 16)
        sheet.paste(picture.resize((cell_w, cell_h)), (x, y + 16))
        draw.text((x + 4, y + 2), f"{label}" + (f"  {timings[label]} s" if label in timings else ""), fill="black")
    sheet.save(OUT / "phase29-expression-spike.png")
    (OUT / "phase29-expression-spike.json").write_text(json.dumps({"shot": str(shot), "seconds": timings}, indent=1), encoding="utf-8")
    print("sheet:", OUT / "phase29-expression-spike.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shot", required=True)
    parser.add_argument("--characters", default="Minh,Lan", help="left to right")
    parser.add_argument("--expressions", default="laugh,surprised,worried,serious,thinking")
    args = parser.parse_args()
    asyncio.run(run(Path(args.shot), [n.strip() for n in args.characters.split(",")],
                    [e.strip() for e in args.expressions.split(",")]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
