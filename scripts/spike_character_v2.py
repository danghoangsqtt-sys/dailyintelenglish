"""Task 20.2c (Phase 20) -- spike v2 runner: SDXL base, a simple character, pose-controlled
M2, and 1280x720 video-frame mockups. Design: .viepilot/phases/20-ai-visuals/tasks/task-20.2c.md

Runs in this project's own `venv/` (Python 3.14) and drives `scripts/image_worker.py`
(in `venv-image/`) through three worker lifetimes, each under a real Task 20.1 GPU lease:

  P1  base text2img      2 scenes in style v2 (calm lower third) + 3 plain-background
                         character candidates (#1 becomes the IP reference)
  P2  base + IP-Adapter  6 identity assets (2 views x 3 expressions) + 1 full body, then
                         **encode** the 4 M2 prompts (with negatives) + the reference
  P3  base ControlNet-   4 M2 renders x 2 pose strengths (strict 1.0 / loose 0.7), pose
      inpaint, no        drawn in scene coordinates, silhouette mask, IP layers only
      encoders
  P4  frames (Pillow)    each M2 render as a 1280x720 frame with the Step-5 overlays and
                         the 20.2d `outline` caption style -- a mockup of the Remotion
                         layout, since the composition has no background-image prop yet

Owner verdicts behind every choice: docs/operations/phase20-spike-character-library.md.
Style rule: descriptive only, never a studio, person or franchise name. No DB access.

**Run it with the app closed**: the GPU lease is process-local (D20.1-g).

    venv\\Scripts\\python scripts\\spike_character_v2.py --run-label r4 > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# Reuses the 20.2b runner's lease/worker plumbing, OpenPose rendering and composite helper
# (scripts/ is sys.path[0] when run as a script; that module also puts the repo on the path).
from spike_character_library import _COLORS, _LIMBS, _Run, keep_scene_outside_mask  # noqa: E402
from spike_images import _checked, _label_tile, _open, _sheet, _WorkerClient  # noqa: E402
from spike_styletts2 import _gpu_snapshot  # noqa: E402

from app.core.config import settings  # noqa: E402

SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20c_character_v2"

# -- prompts (D20.2c-b / D20.2c-c) --------------------------------------------------------

STYLE_V2 = (
    "hand-drawn 2D animation film still, 1990s cel animation look, flat cel shading, "
    "soft painted gouache background, simple clean character design, natural soft daylight, "
    "muted warm earthy palette, gentle nostalgic atmosphere"
)
NEGATIVE_V2 = (
    "3d render, photorealistic, photo, glossy, detailed rendering, cluttered, busy details, "
    "text, letters, logo, watermark, signature, extra fingers, deformed hands, blurry, deformed"
)
CHARACTER_V2 = (
    "a young woman teacher with a short dark brown bob haircut with straight bangs, "
    "wearing a plain mustard-yellow long-sleeve dress"
)
PORTRAIT = "head and shoulders portrait, facing the viewer, relaxed neutral pose, plain light background"
VIEWS_V2 = {
    "front": "head and shoulders portrait, front view facing the viewer, plain light background",
    "three_quarter": "head and shoulders portrait, three-quarter view, head turned to the side, plain light background",
}
EXPRESSIONS_V2 = {
    "neutral": "calm neutral expression",
    "happy": "big happy smile",
    "surprised": "surprised face, raised eyebrows, open mouth",
}
FULL_BODY_V2 = "full body, standing, front view, whole figure visible from head to shoes, plain light background"

# D20.2c-e: presenter framing. Waist-up, on the side away from the vocab card (top-right),
# head below the speaker-chip row (top-left, ends ~11% down).
SCENES_V2 = [
    {"id": "classroom", "cx": 0.30,
     "text": "a cozy sunlit classroom with wooden desks and a chalkboard, plants by the window"},
    {"id": "kitchen", "cx": 0.34,
     "text": "a bright countryside kitchen with a wooden table, a tea kettle and flowers"},
]
SCENE_EXTRA = "calm simple foreground, uncluttered lower part of the picture, empty scene, no people"

# Upper-body OpenPose keypoints in HEAD HEIGHTS (h), relative to the nose, +y down, using
# ordinary adult proportions (shoulders ~1.7h wide, neck-to-hip ~2.4h, arm segments ~1.3h).
# Knees/ankles are below the frame: None (not drawn). COCO order; "r_" is the subject's
# right = image-left for a front view.
_KEYS = ["nose", "neck", "r_shoulder", "r_elbow", "r_wrist", "l_shoulder", "l_elbow", "l_wrist", "r_hip",
         "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle", "r_eye", "l_eye", "r_ear", "l_ear"]
_UPPER_BODY = {
    "nose": (0.0, 0.0), "neck": (0.0, 0.62), "r_shoulder": (-0.85, 0.72), "l_shoulder": (0.85, 0.72),
    "r_elbow": (-0.95, 2.05), "r_wrist": (-0.9, 3.1), "l_elbow": (0.95, 2.05), "l_wrist": (0.9, 3.1),
    "r_hip": (-0.55, 3.0), "l_hip": (0.55, 3.0),
    "r_eye": (-0.13, -0.12), "l_eye": (0.13, -0.12), "r_ear": (-0.3, -0.05), "l_ear": (0.3, -0.05),
}
ACTIONS_V2 = {
    "waving": {"text": "waving hello with one raised hand, happy smile",
               "pose": {"r_elbow": (-1.25, 1.2), "r_wrist": (-1.3, -0.1)}},
    "pointing_up": {"text": "pointing up and to the side with one hand, surprised face",
                    "pose": {"l_elbow": (1.35, 0.55), "l_wrist": (2.1, -0.35)}},
    "explaining": {"text": "explaining with both open hands, friendly smile",
                   "pose": {"r_elbow": (-1.05, 2.0), "r_wrist": (-1.5, 1.55),
                            "l_elbow": (1.05, 2.0), "l_wrist": (1.5, 1.55)}},
    "thinking": {"text": "thinking with a hand on her chin, calm expression",
                 "pose": {"r_elbow": (-0.8, 2.1), "r_wrist": (-0.15, 0.55)}},
}
# Which actions each scene renders (2 per scene), in encode order.
RENDERS = [("classroom", "waving"), ("classroom", "pointing_up"), ("kitchen", "explaining"), ("kitchen", "thinking")]
# Medium close-up presenter framing: head height 0.24 of the frame, head top at ~0.17
# (below the chip row, which ends at ~0.11), hips at the bottom edge (~1.02).
HEAD_H = 0.24
NOSE_Y = 0.30
IP_SCALE_V2 = 0.5  # D20.2c-d (0.7 in 20.2b copied the reference's pose and background)
# D20.2c-f: the owner compares a strict pose against a looser one ("not stiff").
POSE_VARIANTS = {"strict": 1.0, "loose": 0.7}


def _prompt(*parts: str) -> str:
    return ", ".join([STYLE_V2, *parts, "no text, no logo"])


# -- scene-space pose, silhouette mask, frame mockup (pure Pillow, unit-tested) -----------


def scene_pose(action: str, size: tuple[int, int], cx: float, nose_y: float = NOSE_Y,
               head_h: float = HEAD_H) -> list[tuple[float, float] | None]:
    """Pixel keypoints (None = joint not drawn) for one upper-body action in a scene."""
    width, height = size
    unit = head_h * height
    local = {**_UPPER_BODY, **ACTIONS_V2[action]["pose"]}
    points: list[tuple[float, float] | None] = []
    for key in _KEYS:
        if key not in local:
            points.append(None)
            continue
        lx, ly = local[key]
        points.append((cx * width + lx * unit, nose_y * height + ly * unit))
    return points


def draw_pose_pixels(points: list[tuple[float, float] | None], size: tuple[int, int]) -> Image.Image:
    """Standard OpenPose rendering on black (same colours as 20.2b), skipping missing joints."""
    stick = max(2, round(4 * size[1] / 512))
    canvas = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for index, (a, b) in enumerate(_LIMBS):
        pa, pb = points[a - 1], points[b - 1]
        if pa is not None and pb is not None:
            draw.line([pa, pb], fill=tuple(int(c * 0.6) for c in _COLORS[index]), width=stick * 2)
    for index, point in enumerate(points):
        if point is not None:
            x, y = point
            draw.ellipse((x - stick, y - stick, x + stick, y + stick), fill=_COLORS[index])
    return canvas


def silhouette_mask(points: list[tuple[float, float] | None], size: tuple[int, int],
                    head_h: float = HEAD_H) -> Image.Image:
    """D20.2c-f: inpaint only where the character goes -- thick limbs, the torso down to the
    frame edge, a head ellipse enlarged for hair -- dilated and feathered (no rectangle)."""
    height = size[1]
    unit = head_h * height
    p = dict(zip(_KEYS, points, strict=True))
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    arm = max(2, round(0.42 * unit))
    for chain in (("r_shoulder", "r_elbow", "r_wrist"), ("l_shoulder", "l_elbow", "l_wrist")):
        joints = [p[k] for k in chain if p[k] is not None]
        if len(joints) >= 2:
            draw.line(joints, fill=255, width=arm, joint="curve")
        for x, y in joints:  # round caps; the wrist cap is larger for the hand
            r = arm * (0.8 if (x, y) == joints[-1] else 0.5)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
    rs, ls, rh, lh = p["r_shoulder"], p["l_shoulder"], p["r_hip"], p["l_hip"]
    widen = 0.25 * unit
    draw.polygon([(rs[0] - widen, rs[1] - widen), (ls[0] + widen, ls[1] - widen),
                  (lh[0] + widen * 1.5, max(lh[1], height)), (rh[0] - widen * 1.5, max(rh[1], height))], fill=255)
    nx, ny = p["nose"]
    draw.ellipse((nx - 0.62 * unit, ny - 0.78 * unit, nx + 0.62 * unit, ny + 0.62 * unit), fill=255)
    grow = max(3, round(0.1 * unit)) | 1  # MaxFilter needs an odd size
    return mask.filter(ImageFilter.MaxFilter(grow)).filter(ImageFilter.GaussianBlur(max(2, round(0.08 * unit))))


FRAME_SIZE = (1280, 720)
MIDNIGHT = (14, 15, 21)
ACTIVE_WORD = (255, 213, 74)
SPEAKER_COLORS = [(77, 182, 172), (255, 138, 101)]
_FONT_CANDIDATES = {
    True: ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    False: ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES[bold]:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size)


def frame_mockup(render: Image.Image, caption: list[str], active_word: int, speakers: list[str], active_speaker: int,
                 vocab: list[str] | None, progress: float = 0.37) -> Image.Image:
    """The Step-5 Enhanced layout (Episode.tsx geometry) over a full-bleed render: chapter
    bar, speaker chips top-left, vocab card top-right on 85% near-black, and a karaoke
    caption at 10% from the bottom in the 20.2d `outline` style (8-direction 2 px black
    edge + soft glow). A mockup: Remotion has no background-image prop yet (D20.2c-h)."""
    width, height = FRAME_SIZE
    frame = ImageOps.fit(render.convert("RGB"), FRAME_SIZE, method=Image.Resampling.LANCZOS).convert("RGBA")
    overlay = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, width, 6), fill=(255, 255, 255, 38))
    draw.rectangle((0, 0, round(width * progress), 6), fill=(255, 255, 255, 217))
    chip_font, x = _font(22, bold=True), round(width * 0.05)
    for index, name in enumerate(speakers):
        chip_w = round(draw.textlength(name, font=chip_font)) + 40
        active = index == active_speaker
        fill = SPEAKER_COLORS[index % len(SPEAKER_COLORS)] + (255,) if active else MIDNIGHT + (160,)
        draw.rounded_rectangle((x, 36, x + chip_w, 76), 20, fill=fill)
        draw.text((x + 20, 43), name, font=chip_font, fill=(255, 255, 255, 255 if active else 200))
        x += chip_w + 8
    if vocab:
        card_x, card_w = round(width * 0.64), round(width * 0.31)
        draw.rounded_rectangle((card_x, 36, card_x + card_w, 36 + 34 + 28 * (len(vocab) - 1) + 14), 12, fill=MIDNIGHT + (217,))
        for line_index, text in enumerate(vocab):
            font = _font(24, bold=True) if line_index == 0 else _font(18)
            draw.text((card_x + 18, 48 + 28 * line_index + (0 if line_index == 0 else 6)), text, font=font,
                      fill=(255, 255, 255, 240))
    frame = Image.alpha_composite(frame, overlay)

    caption_font = _font(32, bold=True)
    measure = ImageDraw.Draw(frame)
    space = measure.textlength(" ", font=caption_font)
    widths = [measure.textlength(word, font=caption_font) for word in caption]
    total = sum(widths) + space * (len(caption) - 1)
    top = round(height * 0.9) - 40
    glow = Image.new("RGBA", FRAME_SIZE, (0, 0, 0, 0))
    glow_draw, x = ImageDraw.Draw(glow), (width - total) / 2
    for word, word_w in zip(caption, widths, strict=True):
        glow_draw.text((x, top), word, font=caption_font, fill=(0, 0, 0, 230))
        x += word_w + space
    frame = Image.alpha_composite(frame, glow.filter(ImageFilter.GaussianBlur(4)))
    text_draw, x = ImageDraw.Draw(frame), (width - total) / 2
    for index, (word, word_w) in enumerate(zip(caption, widths, strict=True)):
        text_draw.text((x, top), word, font=caption_font, fill=ACTIVE_WORD if index == active_word else (255, 255, 255),
                       stroke_width=2, stroke_fill=(0, 0, 0))
        x += word_w + space
    return frame.convert("RGB")


# Frame copy per render (caption words, active karaoke word, active speaker, vocab card).
FRAME_COPY = {
    ("classroom", "waving"): (["Emma:", "Good", "morning,", "everyone!", "Welcome", "back."], 3, 0, None),
    ("classroom", "pointing_up"): (["Emma:", "Look", "at", "today's", "new", "word!"], 5, 0,
                                   ["vocabulary (noun)", "/vəˈkæbjəˌleri/", "the words someone knows",
                                    "vốn từ vựng"]),
    ("kitchen", "explaining"): (["Emma:", "First,", "we", "boil", "the", "water", "slowly."], 3, 0,
                                ["boil (verb)", "/bɔɪl/", "to heat a liquid until it bubbles", "đun sôi"]),
    ("kitchen", "thinking"): (["Emma:", "Hmm,", "what", "should", "we", "cook", "today?"], 5, 0, None),
}


# -- phases ---------------------------------------------------------------------------


class _RunV2(_Run):
    def __init__(self, args: argparse.Namespace) -> None:  # noqa: D107 -- own paths/report
        self.args = args
        self.out = SPIKE_ROOT / f"run_{args.run_label}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.report: dict[str, Any] = {"run_label": args.run_label, "style_preset": STYLE_V2, "negative": NEGATIVE_V2,
                                       "character": CHARACTER_V2, "ip_scale": IP_SCALE_V2, "phases": {},
                                       "gpu_snapshots": [_gpu_snapshot("start")]}
        self.sources = json.loads(Path(args.sources).read_text(encoding="utf-8")) if args.sources else None

    def _base(self, **fields: Any) -> dict[str, Any]:
        return {"negative_prompt": NEGATIVE_V2, "steps": self.args.steps, **fields}

    def p1_style(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "scenes": [], "candidates": []}
            for index, scene in enumerate(SCENES_V2):
                path = self.out / f"scene_{scene['id']}.png"
                out["scenes"].append(self._gen(worker, f"scene {scene['id']}", **self._base(
                    prompt=_prompt(scene["text"], SCENE_EXTRA), seed=700 + index, width=self.args.scene_size[0],
                    height=self.args.scene_size[1], output_path=str(path))))
            for index in range(3):
                path = self.out / f"candidate_{index + 1}.png"
                out["candidates"].append(self._gen(worker, f"candidate {index + 1}", **self._base(
                    prompt=_prompt(CHARACTER_V2, PORTRAIT, EXPRESSIONS_V2["neutral"]), seed=800 + index,
                    width=self.args.portrait_size[0], height=self.args.portrait_size[1], output_path=str(path))))
            return out
        return body

    def p2_assets(self, reference: Path):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "assets": []}
            out["ip_load"] = self._ip(worker)
            ip = {} if self.args.skip_ip else {"ip_adapter_image": str(reference), "ip_adapter_scale": IP_SCALE_V2}
            for expression, expression_text in EXPRESSIONS_V2.items():
                for view, view_text in VIEWS_V2.items():
                    path = self.out / f"asset_{view}_{expression}.png"
                    response = self._gen(worker, f"asset {view}/{expression}", **self._base(
                        prompt=_prompt(CHARACTER_V2, view_text, expression_text), seed=900,
                        width=self.args.portrait_size[0], height=self.args.portrait_size[1],
                        output_path=str(path), **ip))
                    out["assets"].append({"view": view, "expression": expression, **response})
            path = self.out / "asset_full_body_neutral.png"
            response = self._gen(worker, "asset full_body", **self._base(
                prompt=_prompt(CHARACTER_V2, FULL_BODY_V2, EXPRESSIONS_V2["neutral"]), seed=901,
                width=self.args.fullbody_size[0], height=self.args.fullbody_size[1], output_path=str(path), **ip))
            out["assets"].append({"view": "full_body", "expression": "neutral", **response})
            scene_text = {scene["id"]: scene["text"] for scene in SCENES_V2}
            encode: dict[str, Any] = {
                "command": "encode", "output_path": str(self.out / "m2_embeds.pt"),
                "items": [{"prompt": _prompt(f"in {scene_text[scene_id]}", CHARACTER_V2,
                                             f"waist-up, facing the viewer, {ACTIONS_V2[action]['text']}"),
                           "negative_prompt": NEGATIVE_V2} for scene_id, action in RENDERS]}
            if not self.args.skip_ip:
                encode["ip_adapter_image"] = str(reference)
            out["encode"] = _checked(worker.request(encode), "encode M2 prompts")
            return out
        return body

    def p3_m2(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base", pipeline="controlnet_inpaint", encoders=False),
                                   "renders": []}
            out["ip_load"] = self._ip(worker, with_encoder=False)
            cx = {scene["id"]: scene["cx"] for scene in SCENES_V2}
            for index, (scene_id, action) in enumerate(RENDERS):
                scene_path = self.out / f"scene_{scene_id}.png"
                if not scene_path.is_file():
                    out["renders"].append({"scene": scene_id, "action": action, "status": "missing scene"})
                    continue
                with Image.open(scene_path) as scene_img:
                    scene_rgb = scene_img.convert("RGB")
                points = scene_pose(action, scene_rgb.size, cx[scene_id])
                pose_path, mask_path = self.out / f"pose_{scene_id}_{action}.png", self.out / f"mask_{scene_id}_{action}.png"
                draw_pose_pixels(points, scene_rgb.size).save(pose_path)
                mask = silhouette_mask(points, scene_rgb.size)
                mask.save(mask_path)
                for variant, pose_scale in POSE_VARIANTS.items():
                    raw_path = self.out / f"m2_{scene_id}_{action}_{variant}_raw.png"
                    response = self._gen(worker, f"M2 {scene_id}/{action}/{variant}", embeds_path=str(self.out / "m2_embeds.pt"),
                                         embeds_index=index, seed=1000 + index, steps=self.args.steps,
                                         width=scene_rgb.width, height=scene_rgb.height, output_path=str(raw_path),
                                         init_image=str(scene_path), mask_image=str(mask_path),
                                         control_image=str(pose_path), strength=0.99,
                                         controlnet_conditioning_scale=pose_scale, ip_adapter_scale=IP_SCALE_V2)
                    final_path = self.out / f"m2_{scene_id}_{action}_{variant}.png"
                    with Image.open(raw_path) as raw:
                        keep_scene_outside_mask(scene_rgb, raw, mask).save(final_path)
                    out["renders"].append({"scene": scene_id, "action": action, "variant": variant,
                                           "final_path": str(final_path), **response})
            return out
        return body

    def p4_frames(self) -> dict[str, Any]:
        out: dict[str, Any] = {"frames": []}
        for scene_id, action in RENDERS:
            caption, active_word, active_speaker, vocab = FRAME_COPY[(scene_id, action)]
            for variant in POSE_VARIANTS:
                source = self.out / f"m2_{scene_id}_{action}_{variant}.png"
                if not source.is_file():
                    out["frames"].append({"source": source.name, "status": "missing"})
                    continue
                started = time.monotonic()
                with Image.open(source) as render:
                    path = self.out / f"frame_{scene_id}_{action}_{variant}.png"
                    frame_mockup(render, caption, active_word, ["Emma", "Leo"], active_speaker, vocab).save(path)
                out["frames"].append({"source": source.name, "output_path": str(path),
                                      "wall_time_sec": round(time.monotonic() - started, 3)})
        return out

    def sheets(self) -> dict[str, str | None]:
        o = self.out
        style = _sheet([[_label_tile(_open(str(o / f"scene_{s['id']}.png")), (448, 256), f"scene {s['id']}") for s in SCENES_V2]
                        + [_label_tile(_open(str(o / f"candidate_{i}.png")), (256, 256), f"candidate {i}") for i in (1, 2, 3)]],
                       o / "sheet_style.png")
        rows = [[_label_tile(_open(str(o / f"asset_{v}_{e}.png")), (240, 240), f"{v} {e}") for v in VIEWS_V2]
                for e in EXPRESSIONS_V2]
        rows[0].append(_label_tile(_open(str(o / "asset_full_body_neutral.png")), (164, 240), "full body"))
        character = _sheet(rows, o / "sheet_character.png")
        rows = [[_label_tile(_open(str(o / f"pose_{s}_{a}.png")), (336, 192), f"pose {s} {a}"),
                 _label_tile(_open(str(o / f"mask_{s}_{a}.png")), (336, 192), "mask"),
                 _label_tile(_open(str(o / f"m2_{s}_{a}_strict.png")), (336, 192), "M2 pose strict (1.0)"),
                 _label_tile(_open(str(o / f"m2_{s}_{a}_loose.png")), (336, 192), "M2 pose loose (0.7)")] for s, a in RENDERS]
        m2 = _sheet(rows, o / "sheet_m2.png")
        rows = [[_label_tile(_open(str(o / f"frame_{s}_{a}_{v}.png")), (640, 360), f"{s} {a} (pose {v})") for v in POSE_VARIANTS]
                for s, a in RENDERS]
        frames = _sheet(rows, o / "sheet_frames.png")
        return {"style": style, "character": character, "m2": m2, "frames": frames}


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    run = _RunV2(args)
    await run.phase("p1_style", run.p1_style())
    reference = run.out / "candidate_1.png"
    await run.phase("p2_assets", run.p2_assets(reference))
    await run.phase("p3_m2", run.p3_m2())
    run.report["phases"]["p4_frames"] = run.p4_frames()
    run.report["gpu_snapshots"].append(_gpu_snapshot("end"))
    run.report["sheets"] = run.sheets()
    run.report["output_dir"] = str(run.out)
    return run.report


def _size(value: str) -> tuple[int, int]:
    width, _, height = value.lower().partition("x")
    return int(width), int(height)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 20.2c character spike v2 runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--min-free-mb", type=int, default=8192, help="provisional, as in 20.2/20.2b")
    parser.add_argument("--allow-cpu", action="store_true", help="plumbing check only (no lease, CPU worker)")
    parser.add_argument("--skip-ip", action="store_true", help="plumbing check only: no IP-Adapter anywhere")
    parser.add_argument("--sources", help="JSON of local model paths (offline mirror / plumbing tests)")
    parser.add_argument("--scene-size", type=_size, default=(1344, 768))
    parser.add_argument("--portrait-size", type=_size, default=(1024, 1024))
    parser.add_argument("--fullbody-size", type=_size, default=(832, 1216))
    parser.add_argument("--steps", type=int, default=30)
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_main(_parse_args())), indent=2))
