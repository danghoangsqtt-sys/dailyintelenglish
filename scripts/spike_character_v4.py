"""Task 20.2f (Phase 20) -- spike v4 runner: character-first. Two Vietnamese students in the
r3 watercolor look (exact + bright variant), on SDXL base, with one-pass scenes (character
and scene generated together -- no inpaint, no cut-out). Design:
.viepilot/phases/20-ai-visuals/tasks/task-20.2f.md

Runs in this project's own `venv/` and drives `scripts/image_worker.py` (in `venv-image/`)
through two worker lifetimes, each under a real Task 20.1 GPU lease:

  P1  base text2img      per style x character: 2 head-and-shoulders candidates on a plain
                         light background (the IP reference pool)
  P2  base + IP-Adapter  per style x character (reference = candidate 1): a character
                         sheet (full body + 3 expressions, own seeds) and 2 one-pass scenes
  P3  frames (Pillow)    each scene as a 1280x720 frame with the approved outline captions

Rule (Amendment B §5.1): descriptive styles only, never a studio, person or franchise name;
the characters are invented. No DB access. **Run it with the app closed.**

    venv\\Scripts\\python scripts\\spike_character_v4.py --run-label r6 > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image

# 20.2b lease/worker plumbing; 20.2c frame mockup (scripts/ is sys.path[0] as a script).
from spike_character_library import _Run  # noqa: E402
from spike_character_v2 import frame_mockup  # noqa: E402
from spike_images import _label_tile, _open, _sheet, _WorkerClient  # noqa: E402
from spike_styletts2 import _gpu_snapshot  # noqa: E402

from app.core.config import settings  # noqa: E402

SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20f_character_v4"

# -- prompts (D20.2f-b/c/e) -----------------------------------------------------------------

_R3_HEAD = "hand-painted 2D anime illustration, soft watercolor background, warm natural sunlight"
STYLES = {
    # The exact 20.2b (r3) preset -- the look the owner called "much better".
    "r3_watercolor": f"{_R3_HEAD}, gentle pastel palette, cozy whimsical atmosphere, clean line art",
    # The same, with the owner's "bright colours" request.
    "r3_bright": f"{_R3_HEAD}, bright cheerful colors, clean line art",
}
# CLIP reads 77 tokens (75 + BOS/EOS) and silently drops the rest. Every prompt below was
# counted with OpenAI's CLIP BPE (task-20.2f.md, implementation notes) and fits; "no text,
# no logo" lives only in the negative prompt, which acts on base (CFG 6).
NEGATIVE = ("3d render, photorealistic, photo, text, letters, logo, watermark, signature, blurry, deformed, "
            "extra fingers, deformed hands, bad anatomy")
CHARACTERS = {
    "female_student": "young Vietnamese woman student, long straight black hair, brown eyes, bright yellow sweater, blue jeans",
    "male_student": "young Vietnamese man student, short black hair, brown eyes, bright teal hoodie, dark jeans",
}
SPEAKER = {"female_student": "Linh", "male_student": "Minh"}
CANDIDATE = "head and shoulders portrait, facing the viewer, friendly calm face, plain light background"
SHEET = {  # id -> (text, seed offset, kind)
    "full_body": ("full body, standing, front view, head to shoes, plain light background", 0, "full"),
    "neutral": ("portrait, calm neutral face, plain light background", 1, "portrait"),
    "happy": ("portrait, big happy smile, plain light background", 2, "portrait"),
    "surprised": ("portrait, surprised face, open mouth, plain light background", 3, "portrait"),
}
MEDIUM_SHOT = "medium shot, on the left side"
SCENES = {  # character -> [(scene id, action + place, caption words, active word, vocab card or None)]
    "female_student": [
        ("library", "waving hello in a bright university library",
         ["Linh:", "Hi", "everyone,", "welcome", "to", "the", "library!"], 3, None),
        ("cafe", "reading a book in a cozy Vietnamese street cafe",
         ["Linh:", "This", "book", "is", "really", "fascinating."], 5,
         ["fascinating (adj)", "/ˈfæsɪneɪtɪŋ/", "extremely interesting", "hấp dẫn, lôi cuốn"]),
    ],
    "male_student": [
        ("classroom", "pointing at a whiteboard in a sunny classroom",
         ["Minh:", "Let's", "look", "at", "today's", "new", "word."], 6,
         ["vocabulary (noun)", "/vəˈkæbjəˌleri/", "the words someone knows", "vốn từ vựng"]),
        ("cafe", "talking with open hands in a cozy Vietnamese street cafe",
         ["Minh:", "I", "usually", "order", "iced", "coffee", "here."], 4, None),
    ],
}
IP_SCALE = 0.45


def _prompt(style: str, *parts: str) -> str:
    return ", ".join([STYLES[style], *parts])


class _RunV4(_Run):
    def __init__(self, args: argparse.Namespace) -> None:  # noqa: D107 -- own paths/report
        self.args = args
        self.out = SPIKE_ROOT / f"run_{args.run_label}"
        self.out.mkdir(parents=True, exist_ok=True)
        self.report: dict[str, Any] = {"run_label": args.run_label, "styles": STYLES, "characters": CHARACTERS,
                                       "negative": NEGATIVE, "ip_scale": IP_SCALE, "phases": {},
                                       "gpu_snapshots": [_gpu_snapshot("start")]}
        self.sources = json.loads(Path(args.sources).read_text(encoding="utf-8")) if args.sources else None

    def _base(self, **fields: Any) -> dict[str, Any]:
        return {"negative_prompt": NEGATIVE, "steps": self.args.steps, **fields}

    def p1_candidates(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "candidates": []}
            for s_index, style in enumerate(STYLES):
                for c_index, (character, description) in enumerate(CHARACTERS.items()):
                    for index in range(2):
                        path = self.out / f"{style}_{character}_candidate_{index + 1}.png"
                        out["candidates"].append({"style": style, "character": character, **self._gen(
                            worker, f"{style} {character} candidate {index + 1}", **self._base(
                                prompt=_prompt(style, description, CANDIDATE),
                                seed=2000 + 100 * s_index + 10 * c_index + index,
                                width=self.args.portrait_size[0], height=self.args.portrait_size[1],
                                output_path=str(path)))})
            return out
        return body

    def p2_sheet_and_scenes(self):
        def body(worker: _WorkerClient) -> dict[str, Any]:
            out: dict[str, Any] = {"load": self._load(worker, mode="base"), "sheet": [], "scenes": []}
            out["ip_load"] = self._ip(worker)
            for s_index, style in enumerate(STYLES):
                for c_index, (character, description) in enumerate(CHARACTERS.items()):
                    reference = self.out / f"{style}_{character}_candidate_1.png"
                    ip = {} if self.args.skip_ip else {"ip_adapter_image": str(reference), "ip_adapter_scale": IP_SCALE}
                    seed_base = 3000 + 100 * s_index + 10 * c_index
                    for sheet_id, (text, offset, kind) in SHEET.items():
                        size = self.args.fullbody_size if kind == "full" else self.args.portrait_size
                        path = self.out / f"{style}_{character}_sheet_{sheet_id}.png"
                        out["sheet"].append({"style": style, "character": character, "item": sheet_id, **self._gen(
                            worker, f"{style} {character} sheet {sheet_id}", **self._base(
                                prompt=_prompt(style, description, text), seed=seed_base + offset,
                                width=size[0], height=size[1], output_path=str(path), **ip))})
                    for index, (scene_id, action, *_frame) in enumerate(SCENES[character]):
                        path = self.out / f"{style}_{character}_scene_{scene_id}.png"
                        out["scenes"].append({"style": style, "character": character, "scene": scene_id, **self._gen(
                            worker, f"{style} {character} scene {scene_id}", **self._base(
                                prompt=_prompt(style, description, action, MEDIUM_SHOT), seed=seed_base + 5 + index,
                                width=self.args.scene_size[0], height=self.args.scene_size[1],
                                output_path=str(path), **ip))})
            return out
        return body

    def p3_frames(self) -> dict[str, Any]:
        out: dict[str, Any] = {"frames": []}
        for style in STYLES:
            for character, scenes in SCENES.items():
                for scene_id, _action, caption, active_word, vocab in scenes:
                    source = self.out / f"{style}_{character}_scene_{scene_id}.png"
                    if not source.is_file():
                        out["frames"].append({"source": source.name, "status": "missing"})
                        continue
                    path = self.out / f"frame_{style}_{character}_{scene_id}.png"
                    speakers = [SPEAKER[character], "Minh" if character == "female_student" else "Linh"]
                    with Image.open(source) as render:
                        frame_mockup(render, caption, active_word, speakers, 0, vocab).save(path)
                    out["frames"].append({"source": source.name, "output_path": str(path)})
        return out

    def sheets(self) -> dict[str, str | None]:
        o = self.out
        rows = [[_label_tile(_open(str(o / f"{st}_{ch}_candidate_{i}.png")), (256, 256), f"{st} {ch} #{i}")
                 for ch in CHARACTERS for i in (1, 2)] for st in STYLES]
        candidates = _sheet(rows, o / "sheet_candidates.png")
        rows = [[_label_tile(_open(str(o / f"{st}_{ch}_sheet_{item}.png")), (164, 240) if item == "full_body" else (240, 240),
                             f"{st} {ch} {item}") for item in SHEET] for st in STYLES for ch in CHARACTERS]
        character = _sheet(rows, o / "sheet_character.png")
        rows = [[_label_tile(_open(str(o / f"frame_{st}_{ch}_{sc[0]}.png")), (640, 360), f"{st}: {ch} {sc[0]}")
                 for ch in CHARACTERS for sc in SCENES[ch]] for st in STYLES]
        frames = _sheet(rows, o / "sheet_frames.png")
        return {"candidates": candidates, "character": character, "frames": frames}


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    run = _RunV4(args)
    await run.phase("p1_candidates", run.p1_candidates())
    await run.phase("p2_sheet_scenes", run.p2_sheet_and_scenes())
    run.report["phases"]["p3_frames"] = run.p3_frames()
    run.report["gpu_snapshots"].append(_gpu_snapshot("end"))
    run.report["sheets"] = run.sheets()
    run.report["output_dir"] = str(run.out)
    return run.report


def _size(value: str) -> tuple[int, int]:
    width, _, height = value.lower().partition("x")
    return int(width), int(height)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 20.2f character-first spike v4 runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--min-free-mb", type=int, default=8192, help="provisional, as in the earlier spikes")
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
