r"""Task 20.11 spike: duo third person + top-colour drift. Not shipped.

Runs the real worker (L1 encode -> L2 ControlNet render -> L3 per-person refine; hand repair
skipped, it is unrelated) for duo_close + duo_wide in Cafe + Classroom at two seeds, with the
real locked Lan + Minh faces from data/app.db, in three variants:
  A  today: half-frame IP masks, today's prompts, refine strength 0.55
  B  H1: person-silhouette IP masks
  C  H1 + H2 (count words + negative) + H3 (garment-first refine prompt, strength 0.65)
  D  H1 + no garment words in the duo prompt + "faces visible" + back-view negative, refine 0.65
  E  D with refine strength 0.8

    venv\Scripts\python scripts\spike_duo_fixes.py --out <dir>
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

from app.services.visuals import geometry, recipes  # noqa: E402
from app.services.visuals.engine import WorkerImageEngine  # noqa: E402

SIZE = (1344, 768)
NEGATIVE_C = recipes.NEGATIVE + ", three people, group"
# Round 2 (D/E): round 1 showed no third person but the same colour drift in A/B/C, plus a
# back view in Classroom duo_wide s2. D drops every garment word from the duo prompt (the
# per-person refine paints the outfit); E = D with a stronger refine.
NEGATIVE_D = recipes.NEGATIVE + ", back view, from behind"
REFINE_STRENGTH = {"A": 0.55, "B": 0.55, "C": 0.65, "D": 0.65, "E": 0.8}


def characters(face_dir: str | None = None) -> tuple[list[dict], list[str]]:
    db = sqlite3.connect(ROOT / "data" / "app.db")
    db.row_factory = sqlite3.Row
    people, faces = [], []
    for name in ("Lan", "Minh"):
        row = dict(db.execute("SELECT * FROM characters WHERE name = ?", (name,)).fetchone())
        people.append(row)
        if face_dir:  # round 3: faces kept by a smoke run (`<dir>/<name>/face.png`)
            faces.append(str(Path(face_dir) / name / "face.png"))
            continue
        faces.append(str(ROOT / db.execute(
            "SELECT path FROM character_assets WHERE character_id = ? AND kind = 'face'", (row["id"],)
        ).fetchone()[0]))
    return people, faces


def duo_prompt(left: dict, right: dict, scene: dict, kind: str, variant: str) -> str:
    prompt = recipes.duo_prompt(left, right, scene, kind)
    if variant == "C":
        prompt = prompt.replace("two ", "only two ", 1)
    if variant in ("D", "E"):
        prompt = prompt.replace(recipes.duo_person(left), "a young woman" if left["gender"] == "female" else "a young man")
        prompt = prompt.replace(recipes.duo_person(right), "a young woman" if right["gender"] == "female" else "a young man")
        prompt = prompt.replace("talking face to face", "talking face to face, faces visible")
    return prompt


def refine_prompt(person: dict, scene: dict, variant: str) -> str:
    if variant not in ("C", "D", "E"):
        return recipes.refine_prompt(person, scene)
    noun = "woman" if person["gender"] == "female" else "man"
    return recipes._styled(
        f"plain {person['top_color']} {person['top_item']}, plain {person['bottom_color']} "
        f"{person['bottom_item']}, {person['age_group']} {person['ethnicity']} {noun}, {person['hair']}, "
        f"talking, in {scene['place']}")


async def run(out: Path, variants: list[str], seeds: list[int], face_dir: str | None = None,
              scene_names: list[str] | None = None, kinds: tuple[str, ...] = ("duo_close", "duo_wide")) -> None:
    people, faces = characters(face_dir)
    scenes = [{"name": "Cafe", "place": "a cozy Vietnamese street cafe", "staging": "seated"},
              {"name": "Classroom", "place": "a sunny classroom with a whiteboard", "staging": "standing"}]
    scenes = [scene for scene in scenes if not scene_names or scene["name"] in scene_names]
    jobs = [(variant, scene, kind, seed) for variant in variants for scene in scenes
            for kind in kinds for seed in seeds]
    engine = WorkerImageEngine()
    contexts = []
    for variant, scene, kind, seed in jobs:
        folder = out / f"{variant}_{scene['name']}_{kind}_s{seed}"
        folder.mkdir(parents=True, exist_ok=True)
        persons = geometry.shot_people(kind, scene["staging"], SIZE)
        halves = geometry.half_masks(SIZE)
        if variant == "A":
            masks = list(halves)
        else:
            masks = [geometry.refine_mask(person, SIZE, half) for person, half in zip(persons, halves, strict=True)]
        mask_paths = []
        for index, mask in enumerate(masks):
            path = folder / f"ip_mask_{index}.png"
            mask.save(path)
            mask_paths.append(str(path))
        pose = folder / "pose.png"
        geometry.draw_people(persons, SIZE).save(pose)
        contexts.append({"variant": variant, "scene": scene, "kind": kind, "seed": seed, "folder": folder,
                         "persons": persons, "halves": halves, "masks": mask_paths, "pose": str(pose),
                         "prompt": duo_prompt(people[0], people[1], scene, kind, variant),
                         "negative": {"C": NEGATIVE_C, "D": NEGATIVE_D, "E": NEGATIVE_D}.get(variant, recipes.NEGATIVE)})

    async with engine.session("text2img", ip="with_encoder", consumer="spike_duo_encode") as session:
        for ctx in contexts:
            ctx["embeds"] = ctx["folder"] / "embeds.pt"
            response = await session.request({
                "command": "encode", "output_path": str(ctx["embeds"]), "guidance_scale": 6.0,
                "items": [{"prompt": ctx["prompt"], "negative_prompt": ctx["negative"]}],
                "ip_adapter_images": faces})
            ctx["tokens"] = response["item_tokens"][0]
            print(ctx["folder"].name, "encode", ctx["tokens"], flush=True)

    async with engine.session("controlnet", encoders=False, ip="layers_only", consumer="spike_duo_render") as session:
        for ctx in contexts:
            ctx["raw"] = ctx["folder"] / "raw.png"
            await session.request({
                "command": "generate", "embeds_path": str(ctx["embeds"]), "embeds_index": 0, "seed": ctx["seed"],
                "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                "output_path": str(ctx["raw"]), "control_image": ctx["pose"],
                "controlnet_conditioning_scale": 1.0, "ip_adapter_scale": 0.45, "ip_adapter_masks": ctx["masks"]})
            print(ctx["folder"].name, "render", flush=True)

    async with engine.session("inpaint", ip="with_encoder", consumer="spike_duo_refine") as session:
        for ctx in contexts:
            current = ctx["raw"]
            for index, person in enumerate(ctx["persons"]):
                mask = geometry.refine_mask(person, SIZE, ctx["halves"][index])
                mask_path = ctx["folder"] / f"refine_mask_{index}.png"
                mask.save(mask_path)
                rendered = ctx["folder"] / f"refine_render_{index}.png"
                response = await session.request({
                    "command": "generate", "prompt": refine_prompt(people[index], ctx["scene"], ctx["variant"]),
                    "negative_prompt": ctx["negative"], "seed": ctx["seed"] + 100 + index,
                    "width": SIZE[0], "height": SIZE[1], "steps": 30, "guidance_scale": 6.0,
                    "output_path": str(rendered), "init_image": str(current), "mask_image": str(mask_path),
                    "strength": REFINE_STRENGTH[ctx["variant"]],
                    "ip_adapter_image": faces[index], "ip_adapter_scale": 0.5})
                with Image.open(current) as scene_image, Image.open(rendered) as fixed:
                    merged = Image.composite(fixed.convert("RGB"), scene_image.convert("RGB"), mask)
                current = ctx["folder"] / f"refined_{index}.png"
                merged.save(current)
                print(ctx["folder"].name, "refine", index, response.get("prompt_tokens"), flush=True)
            ctx["final"] = current

    rows = sorted({(c["scene"]["name"], c["kind"], c["seed"]) for c in contexts})
    cw, chh, cap = 448, 256, 16
    sheet = Image.new("RGB", (cw * len(variants), (chh + cap) * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, key in enumerate(rows):
        for col, variant in enumerate(variants):
            ctx = next(c for c in contexts if c["variant"] == variant and
                       (c["scene"]["name"], c["kind"], c["seed"]) == key)
            with Image.open(ctx["final"]) as image:
                image.thumbnail((cw, chh))
                sheet.paste(image, (col * cw, r * (chh + cap) + cap))
            draw.text((col * cw + 4, r * (chh + cap) + 2), f"{variant} {key[0]} {key[1]} s{key[2]}", fill="black")
    sheet.save(out / "contact.png")
    print("done", out / "contact.png", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--variants", default="A,B,C")
    parser.add_argument("--seeds", default="1,2")
    parser.add_argument("--face-dir")
    parser.add_argument("--scenes")
    parser.add_argument("--kinds", default="duo_close,duo_wide")
    args = parser.parse_args()
    asyncio.run(run(Path(args.out), args.variants.split(","), [int(s) for s in args.seeds.split(",")],
                    args.face_dir, args.scenes.split(",") if args.scenes else None, tuple(args.kinds.split(","))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
