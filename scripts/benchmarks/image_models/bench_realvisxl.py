"""Phase 39 benchmark, RealVisXL V5.0 side: the app's real image worker and recipes (run with `.venv`).

    .venv\\Scripts\\python scripts\\benchmarks\\image_models\\bench_realvisxl.py [--only A1,B2] [--tasks activity,plate]

Text-to-image tasks use the session the activity illustrations use (30 steps, CFG 6, 1344x768, tiled VAE); character
inserts use the Task 29.2 recipe (face IP-Adapter at 0.5). Writes PNGs and `results.jsonl` under data/tmp/phase39-bench/.
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import time

from common import OUT, ROOT, VramPeak, bench_set, record, sdxl_prompt

from backend.ai.image.engine import get_image_engine
from backend.core.config import settings

ENGINE = "realvisxl"


def characters() -> dict[str, dict]:
    connection = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    found = {}
    for row in connection.execute("SELECT * FROM characters WHERE name IN ('Alex', 'Lina', 'Jack')"):
        character = dict(row)
        face = connection.execute("SELECT path FROM character_assets WHERE character_id = ? AND kind = 'face'",
                                  (character["id"],)).fetchone()
        character["face_path"] = str((ROOT / face["path"]).resolve()) if face else None
        found[character["name"]] = character
    return found


async def run(items: list[dict], seeds: list[int], size: list[int]) -> None:
    cast = characters()
    engine = get_image_engine()
    plain = [item for item in items if item["task"] != "character"]
    with_face = [item for item in items if item["task"] == "character"]
    for group, session_args in ((plain, {"ip": "none"}), (with_face, {"ip": "with_encoder"})):
        if not group:
            continue
        started = time.monotonic()
        async with engine.session("text2img", consumer="phase39_bench", **session_args) as session:
            record(ENGINE, {"event": "session_ready", "ip": session_args["ip"], "load_s": round(time.monotonic() - started, 1)})
            for item in group:
                character = cast.get(item.get("character", ""))
                prompt, negative = sdxl_prompt(item, character)
                for seed in seeds:
                    path = OUT / ENGINE / f"{item['id']}_s{seed}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    payload = {"command": "generate", "prompt": prompt, "negative_prompt": negative, "seed": seed,
                               "width": size[0], "height": size[1], "steps": 30, "guidance_scale": 6.0,
                               "output_path": str(path)}
                    if character:
                        payload.update({"ip_adapter_image": character["face_path"], "ip_adapter_scale": 0.5})
                    with VramPeak() as vram:
                        tick = time.monotonic()
                        response = await session.request(payload)
                        seconds = time.monotonic() - tick
                    record(ENGINE, {"id": item["id"], "task": item["task"], "seed": seed, "seconds": round(seconds, 1),
                                    "vram_peak_mib": vram.peak, "prompt": prompt, "path": str(path),
                                    "prompt_truncated": response.get("prompt_truncated")})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    parser.add_argument("--tasks", default="")
    args = parser.parse_args()
    data = bench_set()
    items = data["items"]
    if args.only:
        items = [item for item in items if item["id"] in args.only.split(",")]
    if args.tasks:
        items = [item for item in items if item["task"] in args.tasks.split(",")]
    asyncio.run(run(items, data["seeds"], data["size"]))


if __name__ == "__main__":
    main()
