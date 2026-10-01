"""Task 20.2g (Phase 20) -- spike v5 runner: quality tuning on the accepted 20.2f direction
(SDXL base, the r3 watercolor family, one-pass character + scene with IP-Adapter).
Design: .viepilot/phases/20-ai-visuals/tasks/task-20.2g.md

Runs in this project's own `venv/` and drives `scripts/image_worker.py` (in `venv-image/`)
through four worker lifetimes, each under a real Task 20.1 GPU lease:

  P1  base text2img           per style: female x2 + male x4 candidates (clean refs:
                              arms down, plain background; the male is redesigned)
  P2  base + IP-Adapter       per style x character: 3 expression portraits, then
                              **encode** the 2 scene prompts + the reference
  P3  base ControlNet text2img per style x character x scene x 2 seeds: a one-pass scene
      (no encoders, IP layers) with the pose drawn in scene coordinates (left side,
                              medium shot) -- the scene is painted in the same pass
  P4  base inpaint             hand repair: every in-frame hand re-painted at 768^2 from
                              a crop around the known wrist, pasted back feathered
  P5  Pillow                   16 frames with the approved outline captions + 4 sheets

Rule (Amendment B §5.1): descriptive styles only; invented characters. Every prompt fits
CLIP's 77 tokens (20.2f finding F3). No DB access. **Run it with the app closed.**

    venv\\Scripts\\python scripts\\spike_character_v5.py --run-label r7 > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

# 20.2b lease/worker plumbing + OpenPose drawing helpers; 20.2c frame mockup and COCO keys;
# 20.2f styles (scripts/ is sys.path[0] as a script).
from spike_character_library import _Run  # noqa: E402
from spike_character_v2 import _KEYS, _UPPER_BODY, draw_pose_pixels, frame_mockup  # noqa: E402
from spike_character_v4 import STYLES  # noqa: E402
from spike_images import _checked, _label_tile, _open, _sheet, _WorkerClient  # noqa: E402
from spike_styletts2 import _gpu_snapshot  # noqa: E402

from app.core.config import settings  # noqa: E402

SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20g_character_v5"

# -- prompts (D20.2g-a/b/c; all <= 75 CLIP tokens, checked in the cloud session) ------------

NEGATIVE = ("3d render, photorealistic, photo, text, letters, logo, watermark, signature, blurry, deformed, "
            "bad anatomy, extra fingers, deformed hands, hand on face, hand on cheek, backpack, hat, cap, "
            "jacket, coat, scarf")
CHARACTERS = {
    "female_student": "young Vietnamese woman student, long straight black hair, brown eyes, bright yellow sweater, blue jeans",
    "male_student": ("handsome young Vietnamese man student, short black hair, brown eyes, bright friendly smile, "
                     "expressive face, bright teal hoodie, dark jeans"),
}
CANDIDATE_COUNT = {"female_student": 2, "male_student": 4}
CANDIDATE = "head and shoulders portrait, facing the viewer, arms down, plain light background"
EXPRESSIONS = {
    "calm": "portrait, calm friendly face, plain light background",
    "laughing": "portrait, big laughing smile, plain light background",
    "surprised": "portrait, surprised face, open mouth, plain light background",
}
SPEAKER = {"female_student": "Linh", "male_student": "Minh"}
SCENES = {  # character -> [(scene id, action id, prompt text, caption words, active word, vocab card)]
    "female_student": [
        ("library", "waving", "waving hello in a bright university library, medium shot",
         ["Linh:", "Hi", "everyone,", "welcome", "to", "the", "library!"], 3, None),
        ("cafe", "reading", "holding an open book in a cozy Vietnamese street cafe, medium shot",
         ["Linh:", "This", "book", "is", "really", "fascinating."], 5,
         ["fascinating (adj)", "/ˈfæsɪneɪtɪŋ/", "extremely interesting", "hấp dẫn, lôi cuốn"]),
    ],
    "male_student": [
        ("classroom", "pointing", "pointing to the side in a sunny classroom with a whiteboard, medium shot",
         ["Minh:", "Let's", "look", "at", "today's", "new", "word."], 6,
         ["vocabulary (noun)", "/vəˈkæbjəˌleri/", "the words someone knows", "vốn từ vựng"]),
        ("cafe", "talking", "talking with open hands in a cozy Vietnamese street cafe, medium shot",
         ["Minh:", "I", "usually", "order", "iced", "coffee", "here."], 4, None),
    ],
}
IP_SCALE = 0.45
POSE_SCALE = 1.0  # strict, the owner's 20.2c choice
SEEDS_PER_SHOT = 2
HAND_PROMPT = "detailed hand, five fingers, natural hand"
HAND_NEGATIVE = "extra fingers, missing fingers, fused fingers, deformed hands, bad anatomy, blurry"
HAND_STRENGTH = 0.5


def _prompt(style: str, *parts: str) -> str:
    return ", ".join([STYLES[style], *parts])


# -- medium-shot pose geometry (D20.2g-d; pure, unit-tested) -------------------------------

HEAD_H = 0.20  # head height as a fraction of the frame: waist-up, close to the r6 framing the owner liked
NOSE_Y = 0.30
CX = 0.30  # left side: the vocab card lives top-right
_LEGS = {"r_knee": (-0.5, 4.6), "l_knee": (0.5, 4.6)}  # just below the frame edge
ACTIONS = {
    "waving": {"r_elbow": (-1.25, 1.2), "r_wrist": (-1.3, -0.1)},
    "reading": {"r_elbow": (-0.9, 2.1), "r_wrist": (-0.35, 1.7), "l_elbow": (0.9, 2.1), "l_wrist": (0.35, 1.7)},
    "pointing": {"l_elbow": (1.4, 1.0), "l_wrist": (2.4, 0.7)},
    "talking": {"r_elbow": (-1.05, 2.0), "r_wrist": (-1.5, 1.55), "l_elbow": (1.05, 2.0), "l_wrist": (1.5, 1.55)},
}


def medium_shot_pose(action: str, size: tuple[int, int], cx: float = CX, nose_y: float = NOSE_Y,
                     head_h: float = HEAD_H) -> list[tuple[float, float] | None]:
    """Pixel keypoints (COCO order; None = not drawn) for one action, in head-height units."""
    width, height = size
    unit = head_h * height
    local = {**_UPPER_BODY, **_LEGS, **ACTIONS[action]}
    return [None if key not in local else (cx * width + local[key][0] * unit, nose_y * height + local[key][1] * unit)
            for key in _KEYS]


# -- hand repair geometry (D20.2g-e; pure, unit-tested) ------------------------------------

_HANDS = (("r_elbow", "r_wrist"), ("l_elbow", "l_wrist"))


def hand_boxes(points: list[tuple[float, float] | None], size: tuple[int, int],
               head_h: float = HEAD_H) -> list[dict[str, Any]]:
    """One square crop per in-frame hand: centred past the wrist along the forearm, side 2.2
    head-units, clamped inside the frame. Hands whose centre is off-frame are skipped."""
    width, height = size
    unit = head_h * height
    named = dict(zip(_KEYS, points, strict=True))
    side = round(2.2 * unit)
    boxes = []
    for elbow_key, wrist_key in _HANDS:
        elbow, wrist = named[elbow_key], named[wrist_key]
        if elbow is None or wrist is None:
            continue
        cx = wrist[0] + 0.35 * (wrist[0] - elbow[0])
        cy = wrist[1] + 0.35 * (wrist[1] - elbow[1])
        if not (0 <= cx < width and 0 <= cy < height):
            continue
        left = min(max(0, round(cx - side / 2)), width - side)
        top = min(max(0, round(cy - side / 2)), height - side)
        boxes.append({"hand": wrist_key, "box": (left, top, left + side, top + side),
                      "center": (round(cx - left), round(cy - top)), "radius": round(0.9 * unit)})
    return boxes


def hand_mask(side: int, center: tuple[int, int], radius: int) -> Image.Image:
    """Feathered disc around the hand inside its crop (the only region the repair touches)."""
    mask = Image.new("L", (side, side), 0)
    cx, cy = center
    ImageDraw.Draw(mask).ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(max(1, radius // 5)))


def paste_hand(render: Image.Image, fixed_crop: Image.Image, box: tuple[int, int, int, int],
               mask: Image.Image) -> Image.Image:
    """Downscale the repaired crop back into the render through the feathered mask."""
    left, top, right, bottom = box
    out = render.convert("RGB").copy()
    patch = fixed_crop.convert("RGB").resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    region = out.crop(box)
    out.paste(Image.composite(patch, region, mask.resize(patch.size)), (left, top))
    return out


# -- phases ---------------------------------------------------------------------------


def _shots() -> list[tuple[str, str, int, tuple]]:
    """(style, character, seed index, scene tuple) for every render, in a fixed order."""
    return [(style, character, seed, scene) for style in STYLES for character in CHARACTERS
            for scene in SCENES[character] for seed in range(SEEDS_PER_SHOT)]


def _stem(style: str, character: str, scene_id: str, seed: int) -> str:
    return f"{style}_{character}_{scene_id}_s{seed + 1}"


class _RunV5(_Run):
    def __init__(self, args: argparse.Namespace) -> None:  # noqa: D107 -- own paths/report
        self.args = args
        self.out = SPIKE_ROOT / f"run_{args.run_label}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.report: dict[str, Any] = {"run_label": args.run_label, "styles": STYLES, "characters": CHARACTERS,
                                       "negative": NEGATIVE, "ip_scale": IP_SCALE, "pose_scale": POSE_SCALE,
                                       "phases": {}, "gpu_snapshots": [_gpu_snapshot("start")]}
        self.sources = json.loads(Path(args.sources).read_text(encoding="utf-8")) if args.sources else None

    def _base(self, **fields: Any) -> dict[str, Any]:
        return {"negative_prompt": NEGATIVE, "steps": self.args.steps, **fields}

    def p1_candidates(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "candidates": []}
            for s_index, style in enumerate(STYLES):
                for c_index, (character, description) in enumerate(CHARACTERS.items()):
                    for index in range(CANDIDATE_COUNT[character]):
                        path = self.out / f"{style}_{character}_candidate_{index + 1}.png"
                        out["candidates"].append({"style": style, "character": character, **self._gen(
                            worker, f"{style} {character} candidate {index + 1}", **self._base(
                                prompt=_prompt(style, description, CANDIDATE),
                                seed=5000 + 100 * s_index + 10 * c_index + index,
                                width=self.args.portrait_size[0], height=self.args.portrait_size[1],
                                output_path=str(path)))})
            return out
        return body

    def p2_expressions_encode(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "expressions": [], "encode": {}}
            out["ip_load"] = self._ip(worker)
            for s_index, style in enumerate(STYLES):
                for c_index, (character, description) in enumerate(CHARACTERS.items()):
                    reference = self.out / f"{style}_{character}_candidate_1.png"
                    ip = {} if self.args.skip_ip else {"ip_adapter_image": str(reference), "ip_adapter_scale": IP_SCALE}
                    for e_index, (expression, text) in enumerate(EXPRESSIONS.items()):
                        path = self.out / f"{style}_{character}_expr_{expression}.png"
                        out["expressions"].append({"style": style, "character": character, "expression": expression,
                                                   **self._gen(worker, f"{style} {character} {expression}", **self._base(
                                                       prompt=_prompt(style, description, text),
                                                       seed=6000 + 100 * s_index + 10 * c_index + e_index,
                                                       width=self.args.portrait_size[0],
                                                       height=self.args.portrait_size[1], output_path=str(path), **ip))})
                    encode: dict[str, Any] = {
                        "command": "encode", "output_path": str(self.out / f"{style}_{character}_embeds.pt"),
                        "items": [{"prompt": _prompt(style, description, scene[2]), "negative_prompt": NEGATIVE}
                                  for scene in SCENES[character]]}
                    if not self.args.skip_ip:
                        encode["ip_adapter_image"] = str(reference)
                    out["encode"][f"{style}/{character}"] = _checked(worker.request(encode), f"encode {style} {character}")
            return out
        return body

    def p3_scenes(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base", pipeline="controlnet", encoders=False),
                                   "renders": []}
            out["ip_load"] = self._ip(worker, with_encoder=False)
            size = self.args.scene_size
            for index, (style, character, seed, scene) in enumerate(_shots()):
                scene_id, action = scene[0], scene[1]
                stem = _stem(style, character, scene_id, seed)
                pose_path = self.out / f"pose_{character}_{action}.png"
                if not pose_path.is_file():
                    draw_pose_pixels(medium_shot_pose(action, size), size).save(pose_path)
                path = self.out / f"render_{stem}_raw.png"
                out["renders"].append({"stem": stem, "action": action, **self._gen(
                    worker, f"render {stem}", embeds_path=str(self.out / f"{style}_{character}_embeds.pt"),
                    embeds_index=[s[0] for s in SCENES[character]].index(scene_id), seed=7000 + index,
                    steps=self.args.steps, width=size[0], height=size[1], output_path=str(path),
                    control_image=str(pose_path), controlnet_conditioning_scale=POSE_SCALE, ip_adapter_scale=IP_SCALE)})
            return out
        return body

    def p4_hands(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base", pipeline="inpaint"), "hands": []}
            for index, (style, character, seed, scene) in enumerate(_shots()):
                stem = _stem(style, character, scene[0], seed)
                raw_path = self.out / f"render_{stem}_raw.png"
                if not raw_path.is_file():
                    out["hands"].append({"stem": stem, "status": "missing render"})
                    continue
                with Image.open(raw_path) as raw:
                    render = raw.convert("RGB")
                for h_index, hand in enumerate(hand_boxes(medium_shot_pose(scene[1], render.size), render.size)):
                    side = hand["box"][2] - hand["box"][0]
                    crop_path = self.out / f"hand_{stem}_{hand['hand']}_crop.png"
                    mask_path = self.out / f"hand_{stem}_{hand['hand']}_mask.png"
                    fixed_path = self.out / f"hand_{stem}_{hand['hand']}_fixed.png"
                    render.crop(hand["box"]).resize((self.args.hand_size, self.args.hand_size), Image.Resampling.LANCZOS).save(crop_path)
                    scale = self.args.hand_size / side
                    mask = hand_mask(self.args.hand_size, (round(hand["center"][0] * scale), round(hand["center"][1] * scale)),
                                     round(hand["radius"] * scale))
                    mask.save(mask_path)
                    response = self._gen(worker, f"hand {stem} {hand['hand']}", negative_prompt=HAND_NEGATIVE,
                                         prompt=_prompt(style, HAND_PROMPT), steps=self.args.steps,
                                         seed=8000 + 10 * index + h_index, width=self.args.hand_size, height=self.args.hand_size,
                                         output_path=str(fixed_path), init_image=str(crop_path),
                                         mask_image=str(mask_path), strength=HAND_STRENGTH)
                    with Image.open(fixed_path) as fixed:
                        render = paste_hand(render, fixed, hand["box"], hand_mask(side, hand["center"], hand["radius"]))
                    out["hands"].append({"stem": stem, "hand": hand["hand"], "box": hand["box"], **response})
                render.save(self.out / f"render_{stem}_fixed.png")
            return out
        return body

    def p5_frames(self) -> dict[str, Any]:
        out: dict[str, Any] = {"frames": []}
        for style, character, seed, scene in _shots():
            scene_id, _action, _text, caption, active_word, vocab = scene
            stem = _stem(style, character, scene_id, seed)
            source = self.out / f"render_{stem}_fixed.png"
            if not source.is_file():
                source = self.out / f"render_{stem}_raw.png"
            if not source.is_file():
                out["frames"].append({"stem": stem, "status": "missing"})
                continue
            speakers = [SPEAKER[character], "Minh" if character == "female_student" else "Linh"]
            path = self.out / f"frame_{stem}.png"
            with Image.open(source) as render:
                frame_mockup(render, caption, active_word, speakers, 0, vocab).save(path)
            out["frames"].append({"stem": stem, "source": source.name, "output_path": str(path)})
        return out

    def sheets(self) -> dict[str, str | None]:
        o = self.out
        rows = [[_label_tile(_open(str(o / f"{st}_{ch}_candidate_{i + 1}.png")), (220, 220), f"{st} {ch} #{i + 1}")
                 for ch in CHARACTERS for i in range(CANDIDATE_COUNT[ch])] for st in STYLES]
        candidates = _sheet(rows, o / "sheet_candidates.png")
        rows = [[_label_tile(_open(str(o / f"{st}_{ch}_expr_{e}.png")), (240, 240), f"{st} {ch} {e}") for e in EXPRESSIONS]
                for st in STYLES for ch in CHARACTERS]
        expressions = _sheet(rows, o / "sheet_expressions.png")
        rows = [[_label_tile(_open(str(o / f"render_{_stem(st, ch, sc[0], sd)}_raw.png")), (448, 256), f"{st} {ch} {sc[0]} s{sd + 1} RAW"),
                 _label_tile(_open(str(o / f"render_{_stem(st, ch, sc[0], sd)}_fixed.png")), (448, 256), "hands repaired")]
                for st, ch, sd, sc in _shots()]
        hands = _sheet(rows, o / "sheet_hands.png")
        rows = [[_label_tile(_open(str(o / f"frame_{_stem(st, ch, sc[0], sd)}.png")), (480, 270), f"{st}: {ch} {sc[0]} s{sd + 1}")
                 for ch in CHARACTERS for sc in SCENES[ch] for sd in range(SEEDS_PER_SHOT)][i:i + 4]
                for st in STYLES for i in (0, 4)]
        frames = _sheet(rows, o / "sheet_frames.png")
        return {"candidates": candidates, "expressions": expressions, "hands": hands, "frames": frames}


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    run = _RunV5(args)
    await run.phase("p1_candidates", run.p1_candidates())
    await run.phase("p2_expressions_encode", run.p2_expressions_encode())
    await run.phase("p3_scenes", run.p3_scenes())
    await run.phase("p4_hands", run.p4_hands())
    run.report["phases"]["p5_frames"] = run.p5_frames()
    run.report["gpu_snapshots"].append(_gpu_snapshot("end"))
    run.report["sheets"] = run.sheets()
    run.report["output_dir"] = str(run.out)
    return run.report


def _size(value: str) -> tuple[int, int]:
    width, _, height = value.lower().partition("x")
    return int(width), int(height)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 20.2g quality-tuning spike v5 runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--min-free-mb", type=int, default=8192, help="provisional, as in the earlier spikes")
    parser.add_argument("--allow-cpu", action="store_true", help="plumbing check only (no lease, CPU worker)")
    parser.add_argument("--skip-ip", action="store_true", help="plumbing check only: no IP-Adapter anywhere")
    parser.add_argument("--sources", help="JSON of local model paths (offline mirror / plumbing tests)")
    parser.add_argument("--scene-size", type=_size, default=(1344, 768))
    parser.add_argument("--portrait-size", type=_size, default=(1024, 1024))
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--hand-size", type=int, default=768, help="hand-repair crop resolution")
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_main(_parse_args())), indent=2))
