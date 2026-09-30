"""Task 20.2e (Phase 20) -- spike v3 runner: an anime-specialised SDXL (Animagine XL 4.0),
two generic style presets, a face-crop IP reference, and render-then-cut M2.
Design: .viepilot/phases/20-ai-visuals/tasks/task-20.2e.md

Runs in this project's own `venv/` and drives `scripts/image_worker.py` (in `venv-image/`)
through three worker lifetimes, each under a real Task 20.1 GPU lease, both styles per
worker:

  P1  text2img            per style: 2 scenes ("no humans, scenery") + 2 close-up
                          face-reference candidates on a white background
  P2  + IP-Adapter        per style: 4 identity assets (different seeds), then **encode**
                          the 4 M2 prompts (CFG) + the style's reference
  P3  ControlNet-inpaint, per style: 4 strict-pose M2 renders, then anime-seg on each raw
      no encoders, IP     render -> "blend" (20.2c method) and "cut" (character pixels
      layers + anime-seg  only) composites onto the untouched scene
  P4  frames (Pillow)     per style: 4 1280x720 frames from the "cut" composites

Rule (Amendment B §5.1, owner 2026-09-30): styles are generic descriptors. Never a
franchise, character or artist name; every prompt carries `original` and `safe`.
No DB access. **Run it with the app closed** (the GPU lease is process-local).

    venv\\Scripts\\python scripts\\spike_character_v3.py --run-label r5 > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

# 20.2c helpers: scene-space poses, silhouette mask, frame mockup; 20.2b: lease/worker
# plumbing and the outside-the-mask composite (scripts/ is sys.path[0] as a script).
from spike_character_library import _Run, keep_scene_outside_mask  # noqa: E402
from spike_character_v2 import FRAME_COPY, RENDERS, draw_pose_pixels, frame_mockup, scene_pose, silhouette_mask  # noqa: E402
from spike_images import _checked, _label_tile, _open, _sheet, _WorkerClient  # noqa: E402
from spike_styletts2 import _gpu_snapshot  # noqa: E402

from app.core.config import settings  # noqa: E402

SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20e_character_v3"
DEFAULT_BASE_REPO = "cagliostrolab/animagine-xl-4.0"  # CreativeML Open RAIL++-M (D20.2e-a)

# -- prompts (tag syntax: the model is tag-trained; D20.2e-c/d/g) -------------------------

STYLES = {
    "action_webtoon": ("dramatic lighting, rim lighting, cinematic lighting, high contrast, sharp lineart, "
                       "cel shading, detailed eyes, cool color palette, blue and purple lighting, year 2024"),
    "bright_anime": ("anime screencap, soft lighting, bright colors, clean lineart, detailed eyes, sunlight, "
                     "vibrant, year 2024"),
}
QUALITY = "masterpiece, high score, great score, absurdres"
NEGATIVE = ("lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, "
            "worst quality, low quality, low score, bad score, average score, signature, watermark, username, "
            "blurry, logo, nsfw")
CHARACTER = ("mature female, short black hair, bob cut, blunt bangs, blue eyes, white collared shirt, "
             "black jacket")
WHITE_BG = "simple background, white background"
CANDIDATE = f"portrait, close-up, looking at viewer, closed mouth, {WHITE_BG}"
ASSETS = {  # id -> (tags, seed offset); different seeds on purpose (D20.2e-e)
    "front_neutral": (f"portrait, looking at viewer, expressionless, closed mouth, {WHITE_BG}", 0),
    "front_smile": (f"portrait, looking at viewer, smile, open mouth, {WHITE_BG}", 1),
    "side_surprised": (f"portrait, looking to the side, surprised, open mouth, {WHITE_BG}", 2),
    "outfit": (f"cowboy shot, standing, looking at viewer, light smile, {WHITE_BG}", 3),
}
SCENE_TAGS = {
    "classroom": "indoors, classroom, desk, chair, chalkboard, window, plant",
    "kitchen": "indoors, kitchen, wooden table, window, plant, kettle, cup",
}
ACTION_TAGS = {
    "waving": "waving, smile",
    "pointing_up": "pointing up, surprised, open mouth",
    "explaining": "open hands, talking, smile",
    "thinking": "hand on own chin, thinking, closed mouth",
}
SCENE_CX = {"classroom": 0.30, "kitchen": 0.34}  # presenter framing, as in 20.2c
IP_SCALE = 0.4
POSE_SCALE = 1.0  # the owner chose strict (20.2c verdict 3)
GUIDANCE = 5.0  # model card: CFG 4-7, 5 recommended


def character_prompt(style: str, *parts: str) -> str:
    return ", ".join(["1girl, solo, original, safe", CHARACTER, *parts, STYLES[style], QUALITY])


def scene_prompt(style: str, scene_id: str) -> str:
    return ", ".join(["no humans, scenery, original, safe", SCENE_TAGS[scene_id], STYLES[style], QUALITY])


def m2_prompt(style: str, scene_id: str, action: str) -> str:
    return character_prompt(style, "upper body, looking at viewer", ACTION_TAGS[action], SCENE_TAGS[scene_id])


# -- render-then-cut (D20.2e-f; pure Pillow, unit-tested) ----------------------------------


def cut_composite(scene: Image.Image, raw: Image.Image, segmented: Image.Image, mask: Image.Image) -> Image.Image:
    """Paste only the character's own pixels: alpha = anime-seg alpha x hard(silhouette mask),
    feathered 1 px. The model's re-painted background inside the silhouette -- the halo
    the owner saw in 20.2c -- never reaches the frame."""
    size = scene.size
    seg_alpha = np.asarray(segmented.convert("RGBA").getchannel("A").resize(size, Image.Resampling.BILINEAR), dtype=np.uint16)
    hard = np.asarray(mask.convert("L").resize(size), dtype=np.uint16) > 127
    alpha = Image.fromarray((seg_alpha * hard).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))
    return Image.composite(raw.convert("RGB").resize(size), scene.convert("RGB"), alpha)


# -- phases ---------------------------------------------------------------------------


class _RunV3(_Run):
    def __init__(self, args: argparse.Namespace) -> None:  # noqa: D107 -- own paths/report
        self.args = args
        self.out = SPIKE_ROOT / f"run_{args.run_label}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.report: dict[str, Any] = {"run_label": args.run_label, "base_repo": args.base_repo, "styles": STYLES,
                                       "character": CHARACTER, "negative": NEGATIVE, "ip_scale": IP_SCALE,
                                       "pose_scale": POSE_SCALE, "phases": {},
                                       "gpu_snapshots": [_gpu_snapshot("start")]}
        self.sources = json.loads(Path(args.sources).read_text(encoding="utf-8")) if args.sources else None
        self.styles = [s for s in args.styles.split(",") if s]

    def _load(self, worker: _WorkerClient, **fields: Any) -> dict[str, Any]:
        return super()._load(worker, mode="base", base_repo=self.args.base_repo, scheduler="euler_a", **fields)

    def _args(self, **fields: Any) -> dict[str, Any]:
        return {"steps": self.args.steps, "guidance_scale": GUIDANCE, **fields}

    def p1_style(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker), "scenes": [], "candidates": []}
            for s_index, style in enumerate(self.styles):
                for index, scene_id in enumerate(SCENE_TAGS):
                    path = self.out / f"{style}_scene_{scene_id}.png"
                    out["scenes"].append({"style": style, **self._gen(worker, f"{style} scene {scene_id}", **self._args(
                        prompt=scene_prompt(style, scene_id), negative_prompt=NEGATIVE, seed=1100 + 10 * s_index + index,
                        width=self.args.scene_size[0], height=self.args.scene_size[1], output_path=str(path)))})
                for index in range(2):
                    path = self.out / f"{style}_candidate_{index + 1}.png"
                    out["candidates"].append({"style": style, **self._gen(worker, f"{style} candidate {index + 1}", **self._args(
                        prompt=character_prompt(style, CANDIDATE), negative_prompt=NEGATIVE,
                        seed=1200 + 10 * s_index + index, width=self.args.portrait_size[0],
                        height=self.args.portrait_size[1], output_path=str(path)))})
            return out
        return body

    def p2_assets(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker), "assets": [], "encode": {}}
            out["ip_load"] = self._ip(worker)
            for s_index, style in enumerate(self.styles):
                reference = self.out / f"{style}_candidate_1.png"
                ip = {} if self.args.skip_ip else {"ip_adapter_image": str(reference), "ip_adapter_scale": IP_SCALE}
                for asset_id, (tags, seed_offset) in ASSETS.items():
                    size = self.args.fullbody_size if asset_id == "outfit" else self.args.portrait_size
                    path = self.out / f"{style}_asset_{asset_id}.png"
                    out["assets"].append({"style": style, "asset": asset_id, **self._gen(
                        worker, f"{style} asset {asset_id}", **self._args(
                            prompt=character_prompt(style, tags), negative_prompt=NEGATIVE,
                            seed=1300 + 10 * s_index + seed_offset, width=size[0], height=size[1],
                            output_path=str(path), **ip))})
                encode: dict[str, Any] = {
                    "command": "encode", "output_path": str(self.out / f"{style}_m2_embeds.pt"), "guidance_scale": GUIDANCE,
                    "items": [{"prompt": m2_prompt(style, scene_id, action), "negative_prompt": NEGATIVE}
                              for scene_id, action in RENDERS]}
                if not self.args.skip_ip:
                    encode["ip_adapter_image"] = str(reference)
                out["encode"][style] = _checked(worker.request(encode), f"encode {style}")
            return out
        return body

    def p3_m2(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, pipeline="controlnet_inpaint", encoders=False), "renders": []}
            out["ip_load"] = self._ip(worker, with_encoder=False)
            for s_index, style in enumerate(self.styles):
                for index, (scene_id, action) in enumerate(RENDERS):
                    scene_path = self.out / f"{style}_scene_{scene_id}.png"
                    entry: dict[str, Any] = {"style": style, "scene": scene_id, "action": action}
                    if not scene_path.is_file():
                        out["renders"].append({**entry, "status": "missing scene"})
                        continue
                    with Image.open(scene_path) as scene_img:
                        scene_rgb = scene_img.convert("RGB")
                    stem = f"{style}_{scene_id}_{action}"
                    points = scene_pose(action, scene_rgb.size, SCENE_CX[scene_id])
                    pose_path, mask_path = self.out / f"pose_{stem}.png", self.out / f"mask_{stem}.png"
                    draw_pose_pixels(points, scene_rgb.size).save(pose_path)
                    mask = silhouette_mask(points, scene_rgb.size)
                    mask.save(mask_path)
                    raw_path = self.out / f"m2_{stem}_raw.png"
                    entry.update(self._gen(worker, f"M2 {stem}", embeds_path=str(self.out / f"{style}_m2_embeds.pt"),
                                           embeds_index=index, seed=1400 + 10 * s_index + index, steps=self.args.steps,
                                           guidance_scale=GUIDANCE, width=scene_rgb.width, height=scene_rgb.height,
                                           output_path=str(raw_path), init_image=str(scene_path),
                                           mask_image=str(mask_path), control_image=str(pose_path), strength=0.99,
                                           controlnet_conditioning_scale=POSE_SCALE, ip_adapter_scale=IP_SCALE))
                    seg_path = self.out / f"m2_{stem}_seg.png"
                    seg_request: dict[str, Any] = {"command": "remove_background", "input_path": str(raw_path),
                                                   "output_path": str(seg_path)}
                    if self.args.anime_seg_model:
                        seg_request["model_path"] = self.args.anime_seg_model
                    entry["segment"] = _checked(worker.request(seg_request), f"anime-seg {stem}")
                    with Image.open(raw_path) as raw, Image.open(seg_path) as seg:
                        keep_scene_outside_mask(scene_rgb, raw, mask).save(self.out / f"m2_{stem}_blend.png")
                        started = time.monotonic()
                        cut_composite(scene_rgb, raw, seg, mask).save(self.out / f"m2_{stem}_cut.png")
                        entry["cut_sec"] = round(time.monotonic() - started, 3)
                    out["renders"].append(entry)
            return out
        return body

    def p4_frames(self) -> dict[str, Any]:
        out: dict[str, Any] = {"frames": []}
        for style in self.styles:
            for scene_id, action in RENDERS:
                caption, active_word, active_speaker, vocab = FRAME_COPY[(scene_id, action)]
                source = self.out / f"m2_{style}_{scene_id}_{action}_cut.png"
                if not source.is_file():
                    out["frames"].append({"source": source.name, "status": "missing"})
                    continue
                path = self.out / f"frame_{style}_{scene_id}_{action}.png"
                with Image.open(source) as render:
                    frame_mockup(render, caption, active_word, ["Emma", "Leo"], active_speaker, vocab).save(path)
                out["frames"].append({"source": source.name, "output_path": str(path)})
        return out

    def sheets(self) -> dict[str, str | None]:
        o = self.out
        rows = [[_label_tile(_open(str(o / f"{st}_scene_{s}.png")), (448, 256), f"{st} scene {s}") for s in SCENE_TAGS]
                + [_label_tile(_open(str(o / f"{st}_candidate_{i}.png")), (256, 256), f"{st} candidate {i}") for i in (1, 2)]
                for st in self.styles]
        style = _sheet(rows, o / "sheet_style.png")
        rows = [[_label_tile(_open(str(o / f"{st}_asset_{a}.png")), (240, 240) if a != "outfit" else (164, 240), f"{st} {a}")
                 for a in ASSETS] for st in self.styles]
        character = _sheet(rows, o / "sheet_character.png")
        rows = [[_label_tile(_open(str(o / f"pose_{st}_{s}_{a}.png")), (336, 192), f"{st} {s} {a}"),
                 _label_tile(_open(str(o / f"m2_{st}_{s}_{a}_blend.png")), (336, 192), "blend (20.2c method)"),
                 _label_tile(_open(str(o / f"m2_{st}_{s}_{a}_cut.png")), (336, 192), "cut (render-then-cut)")]
                for st in self.styles for s, a in RENDERS]
        m2 = _sheet(rows, o / "sheet_m2.png")
        rows = [[_label_tile(_open(str(o / f"frame_{st}_{s}_{a}.png")), (640, 360), f"{st}: {s} {a}") for st in self.styles]
                for s, a in RENDERS]
        frames = _sheet(rows, o / "sheet_frames.png")
        return {"style": style, "character": character, "m2": m2, "frames": frames}


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    run = _RunV3(args)
    await run.phase("p1_style", run.p1_style())
    await run.phase("p2_assets", run.p2_assets())
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
    parser = argparse.ArgumentParser(description="Task 20.2e character spike v3 runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--min-free-mb", type=int, default=8192, help="provisional, as in 20.2/20.2b/20.2c")
    parser.add_argument("--allow-cpu", action="store_true", help="plumbing check only (no lease, CPU worker)")
    parser.add_argument("--skip-ip", action="store_true", help="plumbing check only: no IP-Adapter anywhere")
    parser.add_argument("--sources", help="JSON of local model paths (offline mirror / plumbing tests)")
    parser.add_argument("--anime-seg-model", help="local isnetis.onnx path instead of the Hub download")
    parser.add_argument("--base-repo", default=DEFAULT_BASE_REPO)
    parser.add_argument("--styles", default=",".join(STYLES))
    parser.add_argument("--scene-size", type=_size, default=(1344, 768))
    parser.add_argument("--portrait-size", type=_size, default=(1024, 1024))
    parser.add_argument("--fullbody-size", type=_size, default=(832, 1216))
    parser.add_argument("--steps", type=int, default=28)
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_main(_parse_args())), indent=2))
