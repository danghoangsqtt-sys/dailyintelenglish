r"""Open-mouth sprite pictures painted on the closed-mouth picture itself (Phase 32, owner review 2026-10-08).

A talking sprite flaps between `<expression>__closed` and `<expression>__open`. When the open picture comes from another image tool
run, its face is drawn again (another head angle, other eyes), so the whole face jumps on every flap. This tool makes the open picture
from the closed one: only a small region around the mouth is repainted (SDXL inpainting on the GPU, `venv-image`) and pasted back, so
the eyes, the face and the head are the same pixels in both pictures.

    venv\Scripts\python scripts\sprite_mouth_inpaint.py alex --mouth 718,374
    venv\Scripts\python scripts\sprite_mouth_inpaint.py lina --mouth 511,516 --names smile__closed,gesture-talk --out D:\some\folder

`--mouth` is the centre of the closed mouth of the calm picture on the 1280 x 1536 canvas; each picture's own mouth is then found near
it (the reddest pixels, the lips). `smile__closed` gives `smile__open`; a gesture `gesture-talk` gives `gesture-talk__open`, so a
character can also talk while making a gesture. The app must not be running (the GPU lease). Results go to
data\assets_sprites\mouths\<character> with a contact sheet, unless `--out` names another folder; they replace nothing in the inbox.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from app.services.visuals.engine import WorkerImageEngine  # noqa: E402

INBOX = ROOT / "data" / "library" / "sprites_inbox"
OUT = ROOT / "data" / "assets_sprites" / "mouths"
EXPRESSIONS = ("calm", "smile", "laugh", "surprised", "thinking", "worried", "serious")
CROP = 384  # the square around the mouth that is repainted (canvas pixels), upscaled to 1024 for the model
MOUTH_RX, MOUTH_RY = 62, 46  # the repainted ellipse around the mouth (canvas pixels)
SEARCH = 70  # how far from the calm mouth a picture's own mouth is looked for (canvas pixels)
MOUTH_WORDS = {
    "calm": "mouth open speaking, saying ah, upper teeth visible",
    "smile": "smiling while speaking, mouth open, teeth visible",
    "laugh": "laughing, wide open smile, teeth visible",
    "surprised": "mouth open in surprise, small round open mouth",
    "thinking": "mouth slightly open, saying hmm",
    "worried": "mouth open speaking, worried",
    "serious": "mouth open speaking, serious",
}
PERSON = {"alex": "a young man", "lina": "a young woman"}
NEGATIVE = "closed mouth, deformed lips, extra teeth, blurry, cartoon, painting, text, watermark"


def find_mouth(picture: Image.Image, near: tuple[int, int]) -> tuple[int, int]:
    """The centre of the lips near `near`: the 3% reddest skin pixels of the window (red over green, relative to brightness)."""
    import numpy as np

    x, y = near
    window = (x - SEARCH, y - SEARCH, x + SEARCH, y + SEARCH)
    data = np.asarray(picture.convert("RGBA").crop(window)).astype(np.float32)
    redness = (data[..., 0] - data[..., 1]) / (data[..., :3].sum(axis=2) + 1)
    redness[data[..., 3] < 200] = -1
    ys, xs = np.where(redness >= np.percentile(redness, 97))
    return int(window[0] + np.median(xs)), int(window[1] + np.median(ys))


def open_name(name: str) -> str:
    return name.replace("__closed", "__open") if name.endswith("__closed") else f"{name}__open"


def words_for(name: str) -> str:
    expression = name.split("__")[0]
    return MOUTH_WORDS.get(expression, MOUTH_WORDS["calm"])


def mouth_mask(size: int, centre: tuple[float, float], scale: float) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    cx, cy = centre
    rx, ry = MOUTH_RX * scale, MOUTH_RY * scale
    ImageDraw.Draw(mask).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(10 * scale / 2))


async def run(who: str, mouth: tuple[int, int], names: list[str], strength: float, out: Path, seed: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    scale = 1024 / CROP
    mouth_mask(1024, (CROP / 2 * scale, CROP / 2 * scale), scale).save(work / "mask.png")
    small_mask = mouth_mask(CROP, (CROP / 2, CROP / 2), 1.0)
    results = []
    engine = WorkerImageEngine()
    async with engine.session("inpaint", consumer="sprite_mouths") as session:
        for name in names:
            closed = Image.open(INBOX / f"{who}__{name}.png").convert("RGBA")
            centre = find_mouth(closed, mouth)
            box = (centre[0] - CROP // 2, centre[1] - CROP // 2, centre[0] + CROP // 2, centre[1] + CROP // 2)
            flat = Image.new("RGBA", closed.size, (128, 128, 128, 255))
            flat.alpha_composite(closed)
            flat.crop(box).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS).save(work / f"init_{name}.png")
            prompt = f"close-up photo of the face of {PERSON.get(who, 'a person')}, {words_for(name)}, natural lips, realistic skin"
            await session.request({
                "command": "generate", "prompt": prompt, "negative_prompt": NEGATIVE, "seed": seed,
                "width": 1024, "height": 1024, "steps": 30, "guidance_scale": 6.0,
                "output_path": str(work / f"out_{name}.png"), "init_image": str(work / f"init_{name}.png"),
                "mask_image": str(work / "mask.png"), "strength": strength,
            })
            painted = Image.open(work / f"out_{name}.png").convert("RGB").resize((CROP, CROP), Image.Resampling.LANCZOS)
            result = closed.copy()
            region = result.crop(box)
            patch = Image.composite(painted.convert("RGBA"), region, small_mask)
            patch.putalpha(region.getchannel("A"))  # the canvas keeps its transparency
            result.paste(patch, box[:2])
            result.save(out / f"{who}__{open_name(name)}.png")
            results.append((name, closed, result, box))
            print(f"{name} -> {open_name(name)} (mouth at {centre})")
    cell = 260
    sheet = Image.new("RGB", (cell * 2, cell * len(results)), "white")
    for row, (name, closed, result, box) in enumerate(results):
        for column, picture in enumerate((closed, result)):
            flat = Image.new("RGBA", picture.size, (150, 150, 150, 255))
            flat.alpha_composite(picture)
            sheet.paste(flat.crop(box).convert("RGB").resize((cell, cell)), (column * cell, row * cell))
    sheet.save(out / "sheet.png")
    print("sheet:", out / "sheet.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("character")
    parser.add_argument("--mouth", required=True, help="x,y of the closed mouth on the canvas")
    parser.add_argument("--names", default=",".join(f"{e}__closed" for e in EXPRESSIONS),
                        help="pictures to open the mouth of, e.g. smile__closed,gesture-talk")
    parser.add_argument("--strength", type=float, default=0.85)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    who = args.character.lower()
    x, y = (int(value) for value in args.mouth.split(","))
    asyncio.run(run(who, (x, y), [n.strip() for n in args.names.split(",") if n.strip()], args.strength,
                    Path(args.out) if args.out else OUT / who, args.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
