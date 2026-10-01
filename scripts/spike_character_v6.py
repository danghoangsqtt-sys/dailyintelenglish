"""Task 20.2h (Phase 20) -- spike v6 runner: two-person conversation shots (masked
multi-face IP-Adapter + a two-skeleton OpenPose), close-up singles, reference cards and
solid-colour 1-top-1-bottom outfits, on the accepted 20.2f/20.2g direction.
Design: .viepilot/phases/20-ai-visuals/tasks/task-20.2h.md

Runs in this project's own `venv/` and drives `scripts/image_worker.py` (in `venv-image/`)
through three worker lifetimes, each under a real Task 20.1 GPU lease:

  P1  base + IP-Adapter        per style x character: a reference card (face from the
                               owner's r7 pick, new solid outfit, plain background); then
                               encode the single + duo prompts (duo = 2 faces, 1 adapter)
  P2  base ControlNet text2img per style: 2 singles + 3 duos, x 2 seeds = 10 renders;
      (no encoders, IP layers) duos confine each face to its half via ip_adapter_masks
  P3  base inpaint             hand repair for every in-frame wrist of every person
  P4  Pillow                   20 frames + 3 sheets

Rule (Amendment B §5.1): descriptive styles only; invented characters; every prompt fits
CLIP's 77 tokens. No DB access. **Run it with the app closed.**

    venv\\Scripts\\python scripts\\spike_character_v6.py --run-label r8 > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

# 20.2b lease/worker plumbing; 20.2c COCO keys, pose drawing, frame mockup; 20.2f styles;
# 20.2g hand repair helpers (scripts/ is sys.path[0] as a script).
from spike_character_library import _Run  # noqa: E402
from spike_character_v2 import _KEYS, _UPPER_BODY, draw_pose_pixels, frame_mockup  # noqa: E402
from spike_character_v4 import STYLES  # noqa: E402
from spike_character_v5 import hand_boxes, hand_mask, paste_hand  # noqa: E402
from spike_images import _checked, _label_tile, _open, _sheet, _WorkerClient  # noqa: E402
from spike_styletts2 import _gpu_snapshot  # noqa: E402

from app.core.config import settings  # noqa: E402

SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20h_character_v6"
R7_DIR = settings.DATA_DIR / "tmp" / "phase20g_character_v5" / "run_r7"

# -- characters and prompts (D20.2h-a/b; all <= 75 CLIP tokens, checked in the cloud) -----

CHARACTERS = {
    "female_student": "young Vietnamese woman student, long straight black hair, brown eyes, plain yellow sweater, plain blue jeans",
    "male_student": ("handsome young Vietnamese man student, short neat black hair, brown eyes, "
                     "plain light blue slim-fit shirt, plain black slim trousers"),
}
SPEAKER = {"female_student": "Linh", "male_student": "Minh"}
# The owner's picks from run r7 (20.2g verdict): each style's female candidate 1, and male
# candidate 1 of r3_bright (the neat-haired one) for both styles.
R7_FACE = {"female_student": "{style}_female_student_candidate_1.png",
           "male_student": "r3_bright_male_student_candidate_1.png"}
CARD = "head and shoulders portrait, facing the viewer, friendly smile, plain light background"
NEGATIVE = ("3d render, photorealistic, photo, text, logo, watermark, blurry, deformed, bad anatomy, extra fingers, "
            "deformed hands, hand on face, backpack, hat, cap, jacket, coat, hoodie, scarf, pattern, stripes, plaid, "
            "print, multicolored clothes, layered clothes, crowd")
DUO = ("two Vietnamese students talking face to face, woman with long black hair in plain yellow sweater on the left, "
       "man with short black hair in plain light blue shirt on the right")
CARD_IP_SCALE = 0.6
IP_SCALE = 0.45
POSE_SCALE = 1.0
SEEDS_PER_SHOT = 2
HAND_PROMPT = "detailed hand, five fingers, natural hand"
HAND_NEGATIVE = "extra fingers, missing fingers, fused fingers, deformed hands, bad anatomy, blurry"
HAND_STRENGTH = 0.5


def _prompt(style: str, *parts: str) -> str:
    return ", ".join([STYLES[style], *parts])


# -- poses (D20.2h-c/d; pure, unit-tested) --------------------------------------------------

_LEGS_STANDING = {"r_knee": (-0.5, 4.6), "l_knee": (0.5, 4.6), "r_ankle": (-0.5, 6.2), "l_ankle": (0.5, 6.2)}


def person_pose(size: tuple[int, int], cx: float, nose_y: float, head_h: float, facing: str = "front",
                arms: dict[str, tuple[float, float]] | None = None,
                legs: dict[str, tuple[float, float]] | None = None) -> list[tuple[float, float] | None]:
    """COCO-18 pixel keypoints (None = not drawn) for one person, in head-height units.
    `facing` "right"/"left" turns the head toward the partner: the nose and eyes shift
    that way, the far ear disappears, and the shoulders narrow to a three-quarter view."""
    width, height = size
    unit = head_h * height
    local = dict(_UPPER_BODY)
    if facing in ("right", "left"):
        sign = 1 if facing == "right" else -1
        local["nose"] = (0.25 * sign, 0.0)
        local["r_eye"] = (-0.13 + 0.15 * sign, -0.12)
        local["l_eye"] = (0.13 + 0.15 * sign, -0.12)
        local.pop("l_ear" if facing == "right" else "r_ear")
        for key in ("r_shoulder", "l_shoulder", "r_hip", "l_hip"):
            x, y = local[key]
            local[key] = (x * 0.8, y)
    local.update(legs or {})
    local.update(arms or {})
    return [None if key not in local else (cx * width + local[key][0] * unit, nose_y * height + local[key][1] * unit)
            for key in _KEYS]


def _single(size: tuple[int, int]) -> list[dict[str, Any]]:
    """Chest-up close-up, one hand gesturing (owner: close-ups preferred)."""
    return [{"head_h": 0.30, "points": person_pose(size, 0.32, 0.36, 0.30, "front",
                                                   {"r_elbow": (-1.0, 1.9), "r_wrist": (-0.6, 1.35)})}]


SHOTS = {  # shot id -> (kind, people geometry builder, place/framing words)
    "single_female_cafe": ("single", _single, "close-up, chest up, talking with a hand gesture, in a cozy Vietnamese street cafe"),
    "single_male_classroom": ("single", _single, "close-up, chest up, talking with a hand gesture, in a sunny classroom"),
    "duo_closeup_cafe": ("duo", lambda size: [
        {"head_h": 0.24, "points": person_pose(size, 0.30, 0.38, 0.24, "right", {"l_elbow": (0.9, 1.9), "l_wrist": (1.3, 1.4)})},
        {"head_h": 0.24, "points": person_pose(size, 0.70, 0.38, 0.24, "left")},
    ], "close-up, in a cozy cafe"),
    "duo_wide_school": ("duo", lambda size: [
        {"head_h": 0.13, "points": person_pose(size, 0.33, 0.30, 0.13, "right", {"l_elbow": (1.0, 1.7), "l_wrist": (1.5, 1.4)},
                                               _LEGS_STANDING)},
        {"head_h": 0.13, "points": person_pose(size, 0.67, 0.30, 0.13, "left", None, _LEGS_STANDING)},
    ], "standing in a sunny classroom"),
    "duo_wide_cafe": ("duo", lambda size: [
        {"head_h": 0.15, "points": person_pose(size, 0.33, 0.32, 0.15, "right", {
            "r_elbow": (-0.9, 2.1), "r_wrist": (0.2, 2.6), "l_elbow": (0.9, 2.1), "l_wrist": (1.0, 2.5)})},
        {"head_h": 0.15, "points": person_pose(size, 0.67, 0.32, 0.15, "left", {
            "r_elbow": (-0.9, 2.1), "r_wrist": (-1.0, 2.5), "l_elbow": (0.9, 2.1), "l_wrist": (-0.2, 2.6)})},
    ], "sitting at a cafe table"),
}
SINGLE_CHARACTER = {"single_female_cafe": "female_student", "single_male_classroom": "male_student"}
FRAME_COPY = {  # shot -> (caption words, active word, active speaker index in [Linh, Minh], vocab card)
    "single_female_cafe": (["Linh:", "This", "cafe", "is", "really", "cozy."], 5, 0,
                           ["cozy (adj)", "/ˈkoʊzi/", "warm and comfortable", "ấm cúng"]),
    "single_male_classroom": (["Minh:", "Let's", "learn", "a", "new", "word", "today."], 5, 1,
                              ["vocabulary (noun)", "/vəˈkæbjəˌleri/", "the words someone knows", "vốn từ vựng"]),
    "duo_closeup_cafe": (["Linh:", "What", "would", "you", "like", "to", "order?"], 4, 0, None),
    "duo_wide_school": (["Minh:", "Did", "you", "finish", "the", "homework?"], 3, 1, None),
    "duo_wide_cafe": (["Linh:", "Let's", "practice", "speaking", "together!"], 3, 0, None),
}


def shot_prompt(style: str, shot: str) -> str:
    kind, _builder, words = SHOTS[shot]
    if kind == "single":
        return _prompt(style, CHARACTERS[SINGLE_CHARACTER[shot]], words)
    return _prompt(style, DUO, words)


def half_masks(size: tuple[int, int]) -> tuple[Image.Image, Image.Image]:
    """IP-Adapter masks for a duo: the female face applies to the left half, the male face
    to the right half (D20.2h-c)."""
    width, height = size
    left, right = Image.new("L", size, 0), Image.new("L", size, 0)
    ImageDraw.Draw(left).rectangle((0, 0, width // 2 - 1, height - 1), fill=255)
    ImageDraw.Draw(right).rectangle((width // 2, 0, width - 1, height - 1), fill=255)
    return left, right


def draw_people(people: list[dict[str, Any]], size: tuple[int, int]) -> Image.Image:
    """One control image holding every skeleton."""
    canvas = Image.new("RGB", size, (0, 0, 0))
    for person in people:
        layer = draw_pose_pixels(person["points"], size)
        canvas = Image.composite(layer, canvas, layer.convert("L").point(lambda v: 255 if v > 0 else 0))
    return canvas


# -- phases ---------------------------------------------------------------------------


def _renders() -> list[tuple[str, str, int]]:
    return [(style, shot, seed) for style in STYLES for shot in SHOTS for seed in range(SEEDS_PER_SHOT)]


def _stem(style: str, shot: str, seed: int) -> str:
    return f"{style}_{shot}_s{seed + 1}"


class _RunV6(_Run):
    def __init__(self, args: argparse.Namespace) -> None:  # noqa: D107 -- own paths/report
        self.args = args
        self.out = SPIKE_ROOT / f"run_{args.run_label}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.r7 = Path(args.r7_dir)
        self.report: dict[str, Any] = {"run_label": args.run_label, "styles": STYLES, "characters": CHARACTERS,
                                       "negative": NEGATIVE, "ip_scale": IP_SCALE, "phases": {},
                                       "gpu_snapshots": [_gpu_snapshot("start")]}
        self.sources = json.loads(Path(args.sources).read_text(encoding="utf-8")) if args.sources else None

    def _ip(self, worker: _WorkerClient, with_encoder: bool = True) -> dict[str, Any] | None:
        if self.args.skip_ip:
            return None
        request: dict[str, Any] = {"command": "load_ip_adapter", **((self.sources or {}).get("ip_adapter") or {})}
        if not with_encoder:
            request["image_encoder_folder"] = None
        return _checked(worker.request(request), "load_ip_adapter")

    def _card(self, style: str, character: str) -> Path:
        return self.out / f"card_{style}_{character}.png"

    def p1_cards_encode(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "cards": [], "encode": {}}
            out["ip_load"] = self._ip(worker)
            blank = self.out / "blank_reference.png"
            Image.new("RGB", (256, 256), (200, 200, 200)).save(blank)
            for s_index, style in enumerate(STYLES):
                for c_index, (character, description) in enumerate(CHARACTERS.items()):
                    face = self.r7 / R7_FACE[character].format(style=style)
                    ip: dict[str, Any] = {}
                    if not self.args.skip_ip:
                        # Missing r7 file: a blank reference at scale 0 (the worker insists on
                        # an IP image while an adapter is loaded) -> a plain no-IP portrait.
                        ip = {"ip_adapter_image": str(face if face.is_file() else blank),
                              "ip_adapter_scale": CARD_IP_SCALE if face.is_file() else 0.0}
                    out["cards"].append({"style": style, "character": character, "r7_face": str(face),
                                         "r7_face_found": face.is_file(), **self._gen(
                                             worker, f"card {style} {character}", negative_prompt=NEGATIVE,
                                             prompt=_prompt(style, description, CARD), steps=self.args.steps,
                                             seed=9000 + 100 * s_index + 10 * c_index,
                                             width=self.args.portrait_size[0], height=self.args.portrait_size[1],
                                             output_path=str(self._card(style, character)), **ip)})
                for shot, (kind, _builder, _words) in SHOTS.items():
                    encode: dict[str, Any] = {"command": "encode", "output_path": str(self.out / f"{style}_{shot}_embeds.pt"),
                                              "items": [{"prompt": shot_prompt(style, shot), "negative_prompt": NEGATIVE}]}
                    if not self.args.skip_ip:
                        if kind == "single":
                            encode["ip_adapter_image"] = str(self._card(style, SINGLE_CHARACTER[shot]))
                        else:
                            encode["ip_adapter_images"] = [str(self._card(style, c)) for c in CHARACTERS]
                    out["encode"][f"{style}/{shot}"] = _checked(worker.request(encode), f"encode {style} {shot}")
            return out
        return body

    def p2_renders(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base", pipeline="controlnet", encoders=False),
                                   "renders": []}
            out["ip_load"] = self._ip(worker, with_encoder=False)
            size = self.args.scene_size
            left, right = half_masks(size)
            mask_paths = [self.out / "mask_left.png", self.out / "mask_right.png"]
            left.save(mask_paths[0])
            right.save(mask_paths[1])
            for index, (style, shot, seed) in enumerate(_renders()):
                kind, builder, _words = SHOTS[shot]
                pose_path = self.out / f"pose_{shot}.png"
                if not pose_path.is_file():
                    draw_people(builder(size), size).save(pose_path)
                extra: dict[str, Any] = {}
                if kind == "duo" and not self.args.skip_ip:
                    extra["ip_adapter_masks"] = [str(p) for p in mask_paths]
                stem = _stem(style, shot, seed)
                out["renders"].append({"stem": stem, "kind": kind, **self._gen(
                    worker, f"render {stem}", embeds_path=str(self.out / f"{style}_{shot}_embeds.pt"), embeds_index=0,
                    seed=11000 + index, steps=self.args.steps, width=size[0], height=size[1],
                    output_path=str(self.out / f"render_{stem}_raw.png"), control_image=str(pose_path),
                    controlnet_conditioning_scale=POSE_SCALE, ip_adapter_scale=IP_SCALE, **extra)})
            return out
        return body

    def p3_hands(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base", pipeline="inpaint"), "hands": []}
            for index, (style, shot, seed) in enumerate(_renders()):
                stem = _stem(style, shot, seed)
                raw_path = self.out / f"render_{stem}_raw.png"
                if not raw_path.is_file():
                    out["hands"].append({"stem": stem, "status": "missing render"})
                    continue
                with Image.open(raw_path) as raw:
                    render = raw.convert("RGB")
                boxes = [box for person in SHOTS[shot][1](render.size)
                         for box in hand_boxes(person["points"], render.size, person["head_h"])]
                for h_index, hand in enumerate(boxes):
                    side = hand["box"][2] - hand["box"][0]
                    tag = f"{stem}_h{h_index}"
                    crop_path, mask_path = self.out / f"hand_{tag}_crop.png", self.out / f"hand_{tag}_mask.png"
                    fixed_path = self.out / f"hand_{tag}_fixed.png"
                    hs = self.args.hand_size
                    render.crop(hand["box"]).resize((hs, hs), Image.Resampling.LANCZOS).save(crop_path)
                    scale = hs / side
                    hand_mask(hs, (round(hand["center"][0] * scale), round(hand["center"][1] * scale)),
                              round(hand["radius"] * scale)).save(mask_path)
                    response = self._gen(worker, f"hand {tag}", negative_prompt=HAND_NEGATIVE,
                                         prompt=_prompt(style, HAND_PROMPT), steps=self.args.steps,
                                         seed=12000 + 10 * index + h_index, width=hs, height=hs,
                                         output_path=str(fixed_path), init_image=str(crop_path),
                                         mask_image=str(mask_path), strength=HAND_STRENGTH)
                    with Image.open(fixed_path) as fixed:
                        render = paste_hand(render, fixed, hand["box"], hand_mask(side, hand["center"], hand["radius"]))
                    out["hands"].append({"stem": stem, "box": hand["box"], **response})
                render.save(self.out / f"render_{stem}_fixed.png")
            return out
        return body

    def p4_frames(self) -> dict[str, Any]:
        out: dict[str, Any] = {"frames": []}
        for style, shot, seed in _renders():
            stem = _stem(style, shot, seed)
            source = self.out / f"render_{stem}_fixed.png"
            if not source.is_file():
                source = self.out / f"render_{stem}_raw.png"
            if not source.is_file():
                out["frames"].append({"stem": stem, "status": "missing"})
                continue
            caption, active_word, active_speaker, vocab = FRAME_COPY[shot]
            path = self.out / f"frame_{stem}.png"
            with Image.open(source) as render:
                frame_mockup(render, caption, active_word, ["Linh", "Minh"], active_speaker, vocab).save(path)
            out["frames"].append({"stem": stem, "source": source.name, "output_path": str(path)})
        return out

    def sheets(self) -> dict[str, str | None]:
        o = self.out
        rows = [[_label_tile(_open(str(self.r7 / R7_FACE[ch].format(style=st))), (220, 220), f"r7 pick {st} {ch}"),
                 _label_tile(_open(str(self._card(st, ch))), (220, 220), f"card {st} {ch}")]
                for st in STYLES for ch in CHARACTERS]
        cards = _sheet(rows, o / "sheet_cards.png")
        rows = [[_label_tile(_open(str(o / f"frame_{_stem(st, sh, sd)}.png")), (480, 270), f"{st}: {sh} s{sd + 1}")
                 for sh in SHOTS for sd in range(SEEDS_PER_SHOT)][i:i + 5] for st in STYLES for i in (0, 5)]
        frames = _sheet(rows, o / "sheet_frames.png")
        rows = [[_label_tile(_open(str(o / f"render_{_stem(st, sh, sd)}_raw.png")), (448, 256), f"{st} {sh} s{sd + 1} RAW"),
                 _label_tile(_open(str(o / f"render_{_stem(st, sh, sd)}_fixed.png")), (448, 256), "hands repaired")]
                for st, sh, sd in _renders()]
        hands = _sheet(rows, o / "sheet_hands.png")
        return {"cards": cards, "frames": frames, "hands": hands}


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    run = _RunV6(args)
    await run.phase("p1_cards_encode", run.p1_cards_encode())
    await run.phase("p2_renders", run.p2_renders())
    await run.phase("p3_hands", run.p3_hands())
    run.report["phases"]["p4_frames"] = run.p4_frames()
    run.report["gpu_snapshots"].append(_gpu_snapshot("end"))
    run.report["sheets"] = run.sheets()
    run.report["output_dir"] = str(run.out)
    return run.report


def _size(value: str) -> tuple[int, int]:
    width, _, height = value.lower().partition("x")
    return int(width), int(height)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 20.2h conversation-shots spike v6 runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--min-free-mb", type=int, default=8192, help="provisional, as in the earlier spikes")
    parser.add_argument("--allow-cpu", action="store_true", help="plumbing check only (no lease, CPU worker)")
    parser.add_argument("--skip-ip", action="store_true", help="plumbing check only: no IP-Adapter anywhere")
    parser.add_argument("--sources", help="JSON of local model paths (offline mirror / plumbing tests)")
    parser.add_argument("--r7-dir", default=str(R7_DIR), help="the r7 run folder holding the owner's picked faces")
    parser.add_argument("--scene-size", type=_size, default=(1344, 768))
    parser.add_argument("--portrait-size", type=_size, default=(1024, 1024))
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--hand-size", type=int, default=768, help="hand-repair crop resolution")
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_main(_parse_args())), indent=2))
