"""Phase 39: contact sheets from the benchmark pictures — one row per subject, one column per engine/seed.

    python scripts\\benchmarks\\image_models\\contact_sheet.py [--engines realvisxl,qwen2512] [--tasks activity] [--blind]

`--blind` hides the engine names (columns shuffled per row with a fixed key written next to the sheet) so the
owner can score without knowing which model drew what.
"""

from __future__ import annotations

import argparse
import json
import random

from PIL import Image, ImageDraw, ImageFont

from common import OUT, bench_set

THUMB = (448, 256)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engines", default="realvisxl")
    parser.add_argument("--tasks", default="")
    parser.add_argument("--blind", action="store_true")
    parser.add_argument("--name", default="sheet")
    args = parser.parse_args()
    engines = args.engines.split(",")
    data = bench_set()
    items = [item for item in data["items"] if not args.tasks or item["task"] in args.tasks.split(",")]
    columns = [(engine, seed) for engine in engines for seed in data["seeds"]]
    font = ImageFont.load_default(size=18)
    label_w = 90
    sheet = Image.new("RGB", (label_w + THUMB[0] * len(columns), 30 + THUMB[1] * len(items)), "white")
    draw = ImageDraw.Draw(sheet)
    key = {}
    rng = random.Random(39)
    for c, (engine, seed) in enumerate(columns):
        if not args.blind:
            draw.text((label_w + c * THUMB[0] + 6, 6), f"{engine} s{seed}", fill="black", font=font)
    for r, item in enumerate(items):
        y = 30 + r * THUMB[1]
        draw.text((6, y + 6), item["id"], fill="black", font=font)
        order = list(columns)
        if args.blind:
            rng.shuffle(order)
            key[item["id"]] = [f"{chr(65 + i)}={engine}:s{seed}" for i, (engine, seed) in enumerate(order)]
        for c, (engine, seed) in enumerate(order):
            path = OUT / engine / f"{item['id']}_s{seed}.png"
            x = label_w + c * THUMB[0]
            if path.is_file():
                with Image.open(path) as image:
                    sheet.paste(image.convert("RGB").resize(THUMB), (x, y))
            if args.blind:
                draw.rectangle((x, y, x + 34, y + 30), fill="black")
                draw.text((x + 8, y + 4), chr(65 + c), fill="white", font=font)
    target = OUT / f"{args.name}.jpg"
    sheet.save(target, quality=88)
    if args.blind:
        (OUT / f"{args.name}.key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
