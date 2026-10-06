"""Task 28.3 smoke: the app's own engine, recipes, skeletons and colour check on RealVisXL V5.0. Not shipped.
Run with the project venv (it imports the app); the image worker runs in venv-image on the GPU.

    venv\\Scripts\\python scripts\\smoke_phase28_t3.py --out data\\tmp\\phase28-smoke
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.services.visuals import colour_check, geometry, recipes  # noqa: E402
from app.services.visuals.engine import WorkerImageEngine  # noqa: E402

SIZE = (1344, 768)
LAN = {"gender": "female", "age_group": "young", "ethnicity": "Vietnamese", "role": "English teacher",
       "hair": "long straight black hair", "eyes": "dark eyes", "top_color": "white", "top_item": "blouse",
       "bottom_color": "white", "bottom_item": "trousers"}
MINH = {"gender": "male", "age_group": "young", "ethnicity": "Vietnamese", "role": "English teacher",
        "hair": "tousled black hair", "eyes": "dark eyes", "top_color": "black", "top_item": "slim-fit shirt",
        "bottom_color": "black", "bottom_item": "slim trousers"}
CAFE = {"place": "a cozy Vietnamese street cafe", "staging": "seated", "time_of_day": "day"}
PARK = {"place": "a quiet city park", "staging": "standing", "time_of_day": "day"}
SEEDS = (7, 21)


def cases():
    """(name, kind, prompt, people) -- the people carry the skeleton and the colour-check boxes."""
    return [
        ("lan_single", "single", recipes.single_prompt(LAN, CAFE), [LAN]),
        ("minh_single", "single", recipes.single_prompt(MINH, PARK), [MINH]),
        ("duo_cafe", "duo_wide", recipes.duo_prompt(LAN, MINH, CAFE, "duo_wide"), [LAN, MINH]),
        ("duo_close", "duo_close", recipes.duo_prompt(LAN, MINH, CAFE, "duo_close"), [LAN, MINH]),
    ]


async def run(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    log, started_all = [], time.monotonic()
    engine = WorkerImageEngine()
    async with engine.session("controlnet", encoders=True, ip="none", consumer="visuals_smoke") as session:
        for name, kind, prompt, characters in cases():
            staging = CAFE["staging"] if kind != "duo_close" else "seated"
            if kind == "single":
                staging = (CAFE if name == "lan_single" else PARK)["staging"]
            people = geometry.shot_people(kind, staging, SIZE)
            pose_path = out / f"{name}_pose.png"
            geometry.draw_people(people, SIZE).save(pose_path)
            for seed in SEEDS:
                path = out / f"{name}_s{seed}.png"
                started = time.monotonic()
                await session.request({
                    "command": "generate", "prompt": prompt, "negative_prompt": recipes.NEGATIVE, "seed": seed,
                    "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                    "output_path": str(path), "control_image": str(pose_path),
                    "controlnet_conditioning_scale": 1.0})
                image = Image.open(path)
                checks = [colour_check.check_person(image, person, character, check_bottom=True)
                          for person, character in zip(people, characters, strict=True)]
                entry = {"case": name, "seed": seed, "sec": round(time.monotonic() - started, 1),
                         "tokens": recipes.token_count(prompt),
                         "checks": [{"who": c["top"]["expected"], "ok": c["ok"],
                                     "top": c["top"]["measured"], "bottom": (c["bottom"] or {}).get("measured")}
                                    for c in checks]}
                log.append(entry)
                print(json.dumps(entry), flush=True)
    summary = {"model": settings.IMAGE_BASE_REPO, "scheduler": settings.IMAGE_SCHEDULER,
               "total_sec": round(time.monotonic() - started_all, 1), "images": len(log),
               "all_checks_ok": all(c["ok"] for entry in log for c in entry["checks"])}
    (out / "log.json").write_text(json.dumps({"summary": summary, "log": log}, indent=1), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "data" / "tmp" / "phase28-smoke"))
    return asyncio.run(run(Path(parser.parse_args().out)))


if __name__ == "__main__":
    sys.exit(main())
