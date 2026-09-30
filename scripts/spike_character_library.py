"""Task 20.2b (Phase 20, Amendment B) -- character library feasibility spike runner.

Runs in this project's own `venv/` (Python 3.14). It drives `scripts/image_worker.py`
(in `venv-image/`) through five worker lifetimes, each under a real Task 20.1 GPU lease,
and answers the four questions the owner approved (task-20.2b.md):

  P1  channel style      2 "no people" scenes + 4 portrait candidates on Lightning, and
                         2 scenes + 1 portrait on base, for a style comparison
  P2  identity           from portrait candidate #1: 3 face views x 5 expressions + full
                         body x 5 expressions (IP-Adapter plus-face), then **encode** the 4
                         action prompts + reference into an embeddings file
  P3  actions            Lightning + ControlNet OpenPose, loaded WITHOUT text/image
                         encoders, renders 4 actions from those embeddings (D20.2b-b: SDXL
                         9.1 + IP 2.0 + ControlNet 2.5 GB would not fit 12 GB together)
  P4  cut-outs           skytnt/anime-seg (ONNX, CPU) on the full-body + action assets
  P5  M1 composites      Pillow, here: naive paste vs integrated (stage spot, contact
                         shadow, colour match, feathered edge)
  P6  M2 render          base inpaint + IP-Adapter: the character painted into each scene,
                         then composited back so the scene stays pixel-identical outside
                         the mask

Style rule (Amendment B §5.1): a descriptive "Ghibli-like" preset. It never names Ghibli,
Miyazaki, a brand, a franchise character or a living artist. "no text, no logo" stays in
the positive prompt, because Lightning at CFG 0 ignores negatives. No DB access at all.

**Run it with the app closed**: the GPU lease is process-local (D20.1-g).

    venv\\Scripts\\python scripts\\spike_character_library.py --run-label r3 > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.exceptions import GpuUnavailableError  # noqa: E402
from app.services.gpu_model_manager import get_gpu_manager  # noqa: E402

# Same worker client, sheet helpers and GPU snapshot as the 20.2 spike (scripts/ is
# sys.path[0] when run as a script).
from spike_images import SpikeError, _checked, _label_tile, _open, _sheet, _WorkerClient  # noqa: E402
from spike_styletts2 import _gpu_snapshot  # noqa: E402

SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20b_character_spike"

# -- prompts (Amendment B §5.1 / D20.2b-e) ---------------------------------------------

STYLE_PRESET = (
    "hand-painted 2D anime illustration, soft watercolor background, warm natural sunlight, "
    "gentle pastel palette, cozy whimsical atmosphere, clean line art"
)
STYLE_NEGATIVE = "3d render, photorealistic, photo, text, letters, logo, watermark, signature, blurry, deformed"
CHARACTER = (
    "a young woman English teacher with short wavy chestnut hair, round glasses, "
    "green cardigan over a white blouse, brown skirt"
)
VIEWS = {
    "front": "head and shoulders portrait, front view facing the viewer",
    "three_quarter_left": "head and shoulders portrait, three-quarter view turned to the left",
    "three_quarter_right": "head and shoulders portrait, three-quarter view turned to the right",
}
FULL_BODY = "full body, standing, front view, whole figure visible from head to shoes, plain light background"
EXPRESSIONS = {
    "neutral": "calm neutral expression",
    "happy": "big happy smile",
    "surprised": "surprised face, raised eyebrows, open mouth",
    "thinking": "thoughtful expression, looking up",
    "sad": "sad expression, downturned mouth",
}
SCENES = [
    {"id": "classroom", "text": "a cozy sunlit classroom with wooden desks and a chalkboard, plants by the window",
     "stage": {"x": 0.72, "floor": 0.95, "height": 0.82}, "action": "waving"},
    {"id": "kitchen", "text": "a bright countryside kitchen with a wooden table, tea kettle and flowers",
     "stage": {"x": 0.30, "floor": 0.95, "height": 0.82}, "action": "pointing"},
]

# D20.2b-d: OpenPose 18-keypoint order (COCO): nose, neck, r_shoulder, r_elbow, r_wrist,
# l_shoulder, l_elbow, l_wrist, r_hip, r_knee, r_ankle, l_hip, l_knee, l_ankle, r_eye,
# l_eye, r_ear, l_ear. "Right" is the subject's right, i.e. image-left for a front view.
_BASE_POSE = [
    (0.50, 0.14), (0.50, 0.22), (0.40, 0.23), (0.37, 0.36), (0.36, 0.48), (0.60, 0.23), (0.63, 0.36), (0.64, 0.48),
    (0.45, 0.50), (0.45, 0.68), (0.45, 0.86), (0.55, 0.50), (0.55, 0.68), (0.55, 0.86),
    (0.48, 0.125), (0.52, 0.125), (0.46, 0.135), (0.54, 0.135),
]


def _pose(**overrides: tuple[float, float]) -> list[tuple[float, float]]:
    names = ["nose", "neck", "r_shoulder", "r_elbow", "r_wrist", "l_shoulder", "l_elbow", "l_wrist", "r_hip",
             "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle", "r_eye", "l_eye", "r_ear", "l_ear"]
    points = list(_BASE_POSE)
    for name, xy in overrides.items():
        points[names.index(name)] = xy
    return points


ACTIONS = {
    "waving": {"text": "waving hello with one raised hand", "pose": _pose(r_elbow=(0.33, 0.20), r_wrist=(0.36, 0.07))},
    "pointing": {"text": "pointing to the side with an outstretched arm",
                 "pose": _pose(l_elbow=(0.72, 0.24), l_wrist=(0.85, 0.23))},
    "thinking": {"text": "thinking with a hand on her chin", "pose": _pose(r_elbow=(0.40, 0.34), r_wrist=(0.49, 0.19))},
    "cheering": {"text": "cheering with both arms raised",
                 "pose": _pose(r_elbow=(0.33, 0.15), r_wrist=(0.30, 0.04), l_elbow=(0.67, 0.15), l_wrist=(0.70, 0.04))},
}
_LIMBS = [(2, 3), (2, 6), (3, 4), (4, 5), (6, 7), (7, 8), (2, 9), (9, 10), (10, 11), (2, 12), (12, 13), (13, 14),
          (2, 1), (1, 15), (15, 17), (1, 16), (16, 18)]
_COLORS = [(255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0), (170, 255, 0), (85, 255, 0), (0, 255, 0),
           (0, 255, 85), (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255), (0, 0, 255), (85, 0, 255),
           (170, 0, 255), (255, 0, 255), (255, 0, 170), (255, 0, 85)]

IP_SCALE = 0.7


def _prompt(*parts: str) -> str:
    return ", ".join([STYLE_PRESET, *parts, "no text, no logo"])


# -- drawing helpers (pure Pillow; unit-tested in the cloud session) --------------------


def draw_openpose(points: list[tuple[float, float]], size: tuple[int, int]) -> Image.Image:
    """Standard OpenPose body rendering on black, as ControlNet OpenPose expects."""
    width, height = size
    stick = max(2, round(4 * height / 512))
    canvas = Image.new("RGB", size, (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    xy = [(x * width, y * height) for x, y in points]
    for index, (a, b) in enumerate(_LIMBS):
        color = tuple(int(c * 0.6) for c in _COLORS[index])
        draw.line([xy[a - 1], xy[b - 1]], fill=color, width=stick * 2)
    for index, (x, y) in enumerate(xy):
        draw.ellipse((x - stick, y - stick, x + stick, y + stick), fill=_COLORS[index])
    return canvas


def _crop_to_alpha(cutout: Image.Image) -> Image.Image:
    bbox = cutout.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    return cutout.crop(bbox) if bbox else cutout


def _placement(scene: Image.Image, cutout: Image.Image, stage: dict[str, float]) -> tuple[Image.Image, tuple[int, int]]:
    target_h = max(1, round(scene.height * stage["height"]))
    target_w = max(1, round(cutout.width * target_h / cutout.height))
    sized = cutout.resize((target_w, target_h), Image.Resampling.LANCZOS)
    left = round(scene.width * stage["x"] - target_w / 2)
    top = round(scene.height * stage["floor"] - target_h)
    return sized, (left, top)


def composite_m1(scene: Image.Image, cutout: Image.Image, stage: dict[str, float], integrated: bool) -> Image.Image:
    """M1 collage. `integrated=False` is the naive paste the owner called "khô cứng"
    (stiff); `integrated=True` adds the Amendment B §5.2 mechanisms: a contact shadow,
    a mild colour/light match to the scene, and a feathered edge."""
    base = scene.convert("RGBA")
    sized, (left, top) = _placement(scene, _crop_to_alpha(cutout.convert("RGBA")), stage)
    if integrated:
        # Mild colour/light match: nudge each channel of the character toward the mean of
        # the scene region it stands in (4th-root ratio, clamped to +/-15%), so a
        # cut-out lit differently from the scene does not look pasted on.
        scene_rgb = np.asarray(scene.convert("RGB"), dtype=np.float32)
        y0, y1 = max(0, top), min(scene.height, top + sized.height)
        x0, x1 = max(0, left), min(scene.width, left + sized.width)
        scene_mean = scene_rgb[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0) if (y1 > y0 and x1 > x0) else scene_rgb.reshape(-1, 3).mean(axis=0)
        char = np.asarray(sized, dtype=np.float32)
        opaque = char[..., 3] > 127
        char_mean = char[..., :3][opaque].mean(axis=0) if opaque.any() else scene_mean
        factors = np.clip((np.maximum(scene_mean, 1.0) / np.maximum(char_mean, 1.0)) ** 0.25, 0.85, 1.15)
        char[..., :3] = np.clip(char[..., :3] * factors, 0, 255)
        matched = Image.fromarray(char.astype(np.uint8), "RGBA")
        sized = Image.merge("RGBA", (*matched.convert("RGB").split(), matched.getchannel("A").filter(ImageFilter.GaussianBlur(1.2))))
        shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
        shadow_w, shadow_h = sized.width * 0.55, max(2, sized.height * 0.07)
        cx, floor = left + sized.width / 2, top + sized.height
        ImageDraw.Draw(shadow).ellipse((cx - shadow_w / 2, floor - shadow_h / 2, cx + shadow_w / 2, floor + shadow_h / 2),
                                       fill=(0, 0, 0, 120))
        base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(max(1, sized.height * 0.025))))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(sized, (left, top), sized)
    return Image.alpha_composite(base, layer).convert("RGB")


def m2_mask(scene_size: tuple[int, int], stage: dict[str, float], aspect: float) -> Image.Image:
    """The inpaint region: the character's stage-spot box, padded 8%, feathered."""
    width, height = scene_size
    box_h = height * stage["height"]
    box_w = box_h * aspect
    cx, floor = width * stage["x"], height * stage["floor"]
    pad_w, pad_h = box_w * 0.08, box_h * 0.08
    mask = Image.new("L", scene_size, 0)
    ImageDraw.Draw(mask).rectangle((cx - box_w / 2 - pad_w, floor - box_h - pad_h, cx + box_w / 2 + pad_w,
                                    min(height, floor + pad_h)), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(max(2, round(height * 0.015))))


def keep_scene_outside_mask(scene: Image.Image, rendered: Image.Image, mask: Image.Image) -> Image.Image:
    """SDXL inpaint re-encodes the whole image; outside the mask the scene must stay the
    approved library scene, pixel for pixel."""
    return Image.composite(rendered.convert("RGB").resize(scene.size), scene.convert("RGB"), mask)


def checkerboard(image: Image.Image, cell: int = 16) -> Image.Image:
    board = Image.new("RGB", image.size, (235, 235, 235))
    draw = ImageDraw.Draw(board)
    for y in range(0, image.height, cell):
        for x in range((y // cell % 2) * cell, image.width, cell * 2):
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(200, 200, 200))
    if image.mode == "RGBA":
        board.paste(image, (0, 0), image)
    return board


# -- phases ---------------------------------------------------------------------------


class _Run:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.out = SPIKE_ROOT / f"run_{args.run_label}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.report: dict[str, Any] = {"run_label": args.run_label, "style_preset": STYLE_PRESET,
                                       "character": CHARACTER, "phases": {}, "gpu_snapshots": [_gpu_snapshot("start")]}
        self.sources = json.loads(Path(args.sources).read_text(encoding="utf-8")) if args.sources else None

    def _load(self, worker: _WorkerClient, **fields: Any) -> dict[str, Any]:
        request = {"command": "load", "lightning_steps": 4, **fields}
        if self.sources:
            request["sources"] = self.sources
        return _checked(worker.request(request), f"load {fields}")

    def _ip(self, worker: _WorkerClient, with_encoder: bool = True) -> dict[str, Any] | None:
        if self.args.skip_ip:
            return None
        request: dict[str, Any] = {"command": "load_ip_adapter"}
        if not with_encoder:
            request["image_encoder_folder"] = None
        return _checked(worker.request(request), "load_ip_adapter")

    def _gen(self, worker: _WorkerClient, what: str, **fields: Any) -> dict[str, Any]:
        return _checked(worker.request({"command": "generate", **fields}), what)

    async def phase(self, name: str, body, needs_gpu: bool = True) -> None:
        """One worker lifetime under its own lease; failures are recorded, not raised."""
        entry: dict[str, Any] = {}
        started = time.monotonic()
        try:
            if needs_gpu and not self.args.allow_cpu:
                async with get_gpu_manager().lease(f"library_{name}", min_free_mb=self.args.min_free_mb) as lease:
                    self.report["gpu_snapshots"].append(_gpu_snapshot(f"{name}_lease_acquired"))
                    entry.update(await asyncio.to_thread(self._run_worker, name, body))
                    self.report["gpu_snapshots"].append(_gpu_snapshot(f"{name}_worker_exited"))
                entry["lease"] = {"free_mb_before": lease.free_mb_before, "free_mb_after_eviction": lease.free_mb_after_eviction,
                                  "evicted_models": lease.evicted_models, "min_free_mb": lease.min_free_mb}
            else:
                entry.update(await asyncio.to_thread(self._run_worker, name, body))
        except GpuUnavailableError as exc:
            entry["error"] = f"lease refused: {exc.reason} (free {exc.free_mb}, need {exc.min_free_mb})"
        except SpikeError as exc:
            entry["error"] = str(exc)
        entry["wall_sec"] = round(time.monotonic() - started, 1)
        self.report["phases"][name] = entry

    def _run_worker(self, name: str, body) -> dict[str, Any]:
        worker = _WorkerClient(f"lib_{name}", self.out, self.args.allow_cpu)
        result: dict[str, Any] = {"handshake": worker.handshake}
        try:
            if worker.handshake.get("status") != "ready":
                raise SpikeError(f"worker not ready: {worker.handshake}")
            result.update(body(worker))
            result["stats"] = worker.request({"command": "stats"})
        except SpikeError as exc:
            result["error"] = str(exc)
        finally:
            worker.close()
        result["worker_exit_code"] = worker.process.returncode
        return result

    # P1 --------------------------------------------------------------------------------
    def p1_style(self, mode: str, portraits: int):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode=mode), "scenes": [], "portraits": []}
            for scene in SCENES:
                path = self.out / f"scene_{scene['id']}_{mode}.png"
                out["scenes"].append(self._gen(worker, f"{mode} scene {scene['id']}",
                                               prompt=_prompt(scene["text"], "empty scene, no people"),
                                               negative_prompt=STYLE_NEGATIVE, seed=500 + SCENES.index(scene),
                                               width=self.args.scene_size[0], height=self.args.scene_size[1],
                                               steps=self.args.base_steps, output_path=str(path)))
            for index in range(portraits):
                path = self.out / f"portrait_{mode}_{index + 1}.png"
                out["portraits"].append(self._gen(worker, f"{mode} portrait {index + 1}",
                                                  prompt=_prompt(CHARACTER, VIEWS["front"], EXPRESSIONS["neutral"]),
                                                  negative_prompt=STYLE_NEGATIVE, seed=100 + index,
                                                  width=self.args.portrait_size[0], height=self.args.portrait_size[1],
                                                  steps=self.args.base_steps, output_path=str(path)))
            return out
        return body

    # P2 --------------------------------------------------------------------------------
    def p2_assets(self, reference: Path):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="lightning"), "assets": []}
            out["ip_load"] = self._ip(worker)
            ip = {} if self.args.skip_ip else {"ip_adapter_image": str(reference), "ip_adapter_scale": IP_SCALE}
            for expression, expression_text in EXPRESSIONS.items():
                for view, view_text in VIEWS.items():
                    path = self.out / f"asset_{view}_{expression}.png"
                    response = self._gen(worker, f"asset {view}/{expression}",
                                         prompt=_prompt(CHARACTER, view_text, expression_text), seed=200,
                                         width=self.args.portrait_size[0], height=self.args.portrait_size[1],
                                         output_path=str(path), **ip)
                    out["assets"].append({"view": view, "expression": expression, **response})
                path = self.out / f"asset_full_body_{expression}.png"
                response = self._gen(worker, f"asset full_body/{expression}",
                                     prompt=_prompt(CHARACTER, FULL_BODY, expression_text), seed=201,
                                     width=self.args.fullbody_size[0], height=self.args.fullbody_size[1],
                                     output_path=str(path), **ip)
                out["assets"].append({"view": "full_body", "expression": expression, **response})
            encode: dict[str, Any] = {"command": "encode", "output_path": str(self.out / "action_embeds.pt"),
                                      "items": [{"prompt": _prompt(CHARACTER, f"full body, {a['text']}",
                                                                   "plain light background")} for a in ACTIONS.values()]}
            if not self.args.skip_ip:
                encode["ip_adapter_image"] = str(reference)
            out["encode"] = _checked(worker.request(encode), "encode actions")
            return out
        return body

    # P3 --------------------------------------------------------------------------------
    def p3_actions(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="lightning", pipeline="controlnet", encoders=False),
                                   "actions": []}
            out["ip_load"] = self._ip(worker, with_encoder=False)
            for index, (name, action) in enumerate(ACTIONS.items()):
                pose_path = self.out / f"pose_{name}.png"
                draw_openpose(action["pose"], self.args.fullbody_size).save(pose_path)
                path = self.out / f"action_{name}.png"
                response = self._gen(worker, f"action {name}", embeds_path=str(self.out / "action_embeds.pt"),
                                     embeds_index=index, seed=300 + index, width=self.args.fullbody_size[0],
                                     height=self.args.fullbody_size[1], output_path=str(path),
                                     control_image=str(pose_path), ip_adapter_scale=IP_SCALE)
                out["actions"].append({"action": name, "pose_path": str(pose_path), **response})
            return out
        return body

    # P4 --------------------------------------------------------------------------------
    def p4_cutouts(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"cutouts": []}
            sources = [self.out / f"asset_full_body_{e}.png" for e in EXPRESSIONS] + [self.out / f"action_{a}.png" for a in ACTIONS]
            for source in sources:
                if not source.is_file():
                    out["cutouts"].append({"input": source.name, "status": "missing"})
                    continue
                request: dict[str, Any] = {"command": "remove_background", "input_path": str(source),
                                           "output_path": str(self.out / f"cut_{source.stem}.png")}
                if self.args.anime_seg_model:
                    request["model_path"] = self.args.anime_seg_model
                out["cutouts"].append({"input": source.name, **_checked(worker.request(request), f"cut-out {source.name}")})
            return out
        return body

    # P5 (no worker) --------------------------------------------------------------------
    def p5_m1(self) -> dict[str, Any]:
        out: dict[str, Any] = {"composites": []}
        for scene in SCENES:
            scene_path = self.out / f"scene_{scene['id']}_lightning.png"
            cut_path = self.out / f"cut_action_{scene['action']}.png"
            if not (scene_path.is_file() and cut_path.is_file()):
                out["composites"].append({"scene": scene["id"], "status": "missing inputs"})
                continue
            with Image.open(scene_path) as scene_img, Image.open(cut_path) as cut_img:
                for integrated in (False, True):
                    path = self.out / f"m1_{scene['id']}_{'integrated' if integrated else 'naive'}.png"
                    started = time.monotonic()
                    composite_m1(scene_img, cut_img, scene["stage"], integrated).save(path)
                    out["composites"].append({"scene": scene["id"], "integrated": integrated, "output_path": str(path),
                                              "wall_time_sec": round(time.monotonic() - started, 3)})
        return out

    # P6 --------------------------------------------------------------------------------
    def p6_m2(self, reference: Path):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base", pipeline="inpaint"), "renders": []}
            out["ip_load"] = self._ip(worker)
            ip = {} if self.args.skip_ip else {"ip_adapter_image": str(reference), "ip_adapter_scale": IP_SCALE}
            for scene in SCENES:
                scene_path = self.out / f"scene_{scene['id']}_lightning.png"
                if not scene_path.is_file():
                    out["renders"].append({"scene": scene["id"], "status": "missing scene"})
                    continue
                with Image.open(scene_path) as scene_img:
                    scene_rgb = scene_img.convert("RGB")
                mask = m2_mask(scene_rgb.size, scene["stage"], aspect=0.42)
                mask_path = self.out / f"m2_mask_{scene['id']}.png"
                mask.save(mask_path)
                raw_path = self.out / f"m2_{scene['id']}_raw.png"
                response = self._gen(worker, f"M2 {scene['id']}",
                                     prompt=_prompt(scene["text"], CHARACTER, f"full body, {ACTIONS[scene['action']]['text']}"),
                                     negative_prompt=STYLE_NEGATIVE, seed=600 + SCENES.index(scene),
                                     width=scene_rgb.width, height=scene_rgb.height, steps=self.args.base_steps,
                                     output_path=str(raw_path), init_image=str(scene_path), mask_image=str(mask_path),
                                     strength=0.99, **ip)
                with Image.open(raw_path) as raw:
                    final_path = self.out / f"m2_{scene['id']}.png"
                    keep_scene_outside_mask(scene_rgb, raw, mask).save(final_path)
                out["renders"].append({"scene": scene["id"], "final_path": str(final_path), **response})
            return out
        return body

    # sheets ----------------------------------------------------------------------------
    def sheets(self) -> dict[str, str | None]:
        o, t = self.out, (360, 203)
        rows = []
        for mode, portraits in (("lightning", 4), ("base", 1)):
            row = [_label_tile(_open(str(o / f"scene_{s['id']}_{mode}.png")), t, f"{mode} {s['id']}") for s in SCENES]
            row += [_label_tile(_open(str(o / f"portrait_{mode}_{i + 1}.png")), (203, 203), f"{mode} portrait {i + 1}")
                    for i in range(portraits)]
            rows.append(row)
        style = _sheet(rows, o / "sheet_style.png")
        rows = [[_label_tile(_open(str(o / f"asset_{v}_{e}.png")), (220, 220) if v != "full_body" else (152, 220), f"{v} {e}")
                 for v in [*VIEWS, "full_body"]] for e in EXPRESSIONS]
        character = _sheet(rows, o / "sheet_character.png")
        rows = []
        for name in ACTIONS:
            cut = _open(str(o / f"cut_action_{name}.png"))
            rows.append([_label_tile(_open(str(o / f"pose_{name}.png")), (160, 234), f"pose {name}"),
                         _label_tile(_open(str(o / f"action_{name}.png")), (160, 234), f"action {name}"),
                         _label_tile(checkerboard(cut) if cut else None, (160, 234), "cut-out")])
        actions = _sheet(rows, o / "sheet_actions.png")
        rows = [[_label_tile(_open(str(o / f"m1_{s['id']}_naive.png")), t, "M1 naive paste"),
                 _label_tile(_open(str(o / f"m1_{s['id']}_integrated.png")), t, "M1 integrated"),
                 _label_tile(_open(str(o / f"m2_{s['id']}.png")), t, "M2 render")] for s in SCENES]
        composites = _sheet(rows, o / "sheet_composites.png")
        return {"style": style, "character": character, "actions": actions, "composites": composites}


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    run = _Run(args)
    await run.phase("p1_style_lightning", run.p1_style("lightning", 4))
    if not args.skip_base_style:
        await run.phase("p1_style_base", run.p1_style("base", 1))
    reference = run.out / "portrait_lightning_1.png"
    await run.phase("p2_assets", run.p2_assets(reference))
    await run.phase("p3_actions", run.p3_actions())
    await run.phase("p4_cutouts", run.p4_cutouts(), needs_gpu=False)
    run.report["phases"]["p5_m1"] = run.p5_m1()
    await run.phase("p6_m2", run.p6_m2(reference))
    run.report["gpu_snapshots"].append(_gpu_snapshot("end"))
    run.report["sheets"] = run.sheets()
    run.report["output_dir"] = str(run.out)
    return run.report


def _size(value: str) -> tuple[int, int]:
    width, _, height = value.lower().partition("x")
    return int(width), int(height)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 20.2b character library spike runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--min-free-mb", type=int, default=8192, help="provisional, as in 20.2")
    parser.add_argument("--allow-cpu", action="store_true", help="plumbing check only (no lease, CPU worker)")
    parser.add_argument("--skip-ip", action="store_true", help="plumbing check only: no IP-Adapter anywhere")
    parser.add_argument("--skip-base-style", action="store_true")
    parser.add_argument("--sources", help="JSON of local model paths (offline mirror / plumbing tests)")
    parser.add_argument("--anime-seg-model", help="local isnetis.onnx path instead of the Hub download")
    parser.add_argument("--scene-size", type=_size, default=(1344, 768))
    parser.add_argument("--portrait-size", type=_size, default=(1024, 1024))
    parser.add_argument("--fullbody-size", type=_size, default=(832, 1216))
    parser.add_argument("--base-steps", type=int, default=30)
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_main(_parse_args())), indent=2))
