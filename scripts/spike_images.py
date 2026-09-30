"""Task 20.2 (Phase 20) -- local image model spike runner.

Runs in this project's own `venv/` (Python 3.14). Candidates follow task-20.2.md
Amendment A (owner, 2026-09-30): the channel is monetized, and everything must be free,
need no registration and carry no vendor watermark. So:
- **A / `base`**: SDXL base 1.0 fp16 + the fp16-fix VAE, full steps (the quality
  reference);
- **A-fast / `lightning`**: SDXL-Lightning's 4-step UNet on the same base (the speed
  option);
- **IP**: `ip-adapter-plus-face_sdxl_vit-h`, run on both, as the consistent-character
  trial.
SDXL-Turbo (registration) and FLUX.1-schnell (no commercial IP-Adapter, ~18 GB, tight RAM)
are out.

What it does:
  1. Reads 5 real episodes `mode=ro` (topic + the thumbnail that ships today, as the
     baseline).
  2. Optionally (`--warm-qwen`) makes one real local qwen call through the app's own
     `OllamaProvider` (`num_ctx=16384`, `keep_alive 5m`), so the first image lease has to
     evict qwen for real. This produces Task 20.1's owed evidence: free VRAM with the
     app's qwen, VRAM before and after eviction, and qwen reload time.
  3. For each candidate: takes a real Task 20.1 GPU lease, spawns `scripts/image_worker.py`
     in `venv-image/`, generates one 16:9 background per episode, then the IP-Adapter
     sheet (a portrait reference + 3 scenes at 2 adapter strengths), and exits. The worker
     exiting is what returns the VRAM.
  4. Writes per-episode contact sheets (today's template | base | lightning), the
     IP-Adapter sheet, and prints a JSON measurement block.
     `docs/operations/phase20-spike-images.md` is filled in by hand from it.

**Run it with the app closed.** The lease is process-local (Task 20.1 D20.1-g): this
script's lease does not coordinate with a running app's lease. Ollama eviction still
works, since it is HTTP.

Usage (owner's machine):
    venv\\Scripts\\python scripts\\spike_images.py --run-label idle
    venv\\Scripts\\python scripts\\spike_images.py --run-label warm_qwen --warm-qwen
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import aiosqlite
from PIL import Image, ImageDraw, ImageFont, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.exceptions import GpuUnavailableError, NotFoundError, ProviderError  # noqa: E402
from app.services.ai.contracts import GenerationRequest  # noqa: E402
from app.services.ai.ollama_provider import OllamaProvider  # noqa: E402
from app.services.gpu_model_manager import get_gpu_manager  # noqa: E402
from app.services.thumbnail_service import _resolve_content_sync  # noqa: E402

# `scripts/` is sys.path[0] when run as a script; same nvidia-smi + ollama ps snapshot
# as the 21.1b spike, so both spikes' GPU evidence has one shape.
from spike_styletts2 import _gpu_snapshot  # noqa: E402

VENV_IMAGE_DIR = PROJECT_ROOT / "venv-image"
IMAGE_WORKER_PYTHON = VENV_IMAGE_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
IMAGE_WORKER_SCRIPT = PROJECT_ROOT / "scripts" / "image_worker.py"
SPIKE_ROOT = settings.DATA_DIR / "tmp" / "phase20_image_spike"

EPISODE_COUNT = 5
# Fixed seeds, so a re-run (or the other candidate) starts from the same noise.
EPISODE_SEED_BASE = 2020
REFERENCE_SEED = 777
SCENE_SEED_BASE = 3030
IP_ADAPTER_SCALES = (0.5, 0.8)

# D20.2-c + Amendment A's prompt rule: never a brand, a franchise character or a living
# artist -- generic "original character" styles only. The subject comes first because
# CLIP truncates at 77 tokens. The "no text" wording lives in the POSITIVE prompt too,
# because Lightning runs at CFG 0, where diffusers ignores the negative prompt entirely
# (the worker reports `negative_prompt_applied`).
BACKGROUND_PROMPT = (
    "{subject}, an original friendly cartoon character in modern 3D animation style, "
    "bright cheerful colors, soft lighting, simple clean background, empty space on the left, "
    "no text, no letters, no logo"
)
NEGATIVE_PROMPT = "text, letters, words, caption, logo, watermark, signature, brand name, blurry, lowres, deformed"
REFERENCE_PROMPT = (
    "head and shoulders portrait of an original friendly cartoon English teacher character, "
    "modern 3D animation style, warm smile, plain light background, no text"
)
SCENE_PROMPTS = (
    "the same friendly cartoon English teacher character waving hello in a sunny classroom, modern 3D animation style, no text",
    "the same friendly cartoon English teacher character reading a book in a cozy library, modern 3D animation style, no text",
    "the same friendly cartoon English teacher character pointing at a whiteboard, modern 3D animation style, no text",
)

# Provisional lease threshold (D20.2-e), stated as provisional in the report. Rough fp16
# weights: A ≈ 6.9 GB, plus the IP-Adapter and ViT-H encoder ≈ 1.7 GB, so about 8.6 GB
# before activations. It must also stay under the ~10286 MiB free that the owner's card
# shows at idle (task-21.1b.md D21.1b-e), otherwise the lease would refuse even an idle
# machine. The measured peak from this spike replaces it as DIE_GPU_MIN_FREE_MB_IMAGE.
PROVISIONAL_MIN_FREE_MB = 9216

WORKER_EXIT_TIMEOUT_SECONDS = 120.0


class SpikeError(RuntimeError):
    """Stops the spike before it measures anything misleading."""


# -- inputs --------------------------------------------------------------------------


async def _fetch_episodes(db: aiosqlite.Connection, project_ids: list[str] | None) -> list[dict[str, Any]]:
    """Real episodes plus the thumbnail that ships today (the selected one, else variant 0)."""
    thumb_subquery = (
        "(SELECT image_path_16x9 FROM thumbnails t WHERE t.project_id = p.id "
        "ORDER BY t.is_selected DESC, t.variant_index LIMIT 1)"
    )
    if project_ids:
        placeholders = ",".join("?" for _ in project_ids)
        cursor = await db.execute(
            f"SELECT p.id, p.name, p.topic, p.cefr_level, {thumb_subquery} AS thumb "
            f"FROM projects p WHERE p.id IN ({placeholders})",
            project_ids,
        )
    else:
        # Episodes that already have a template thumbnail come first, so the owner
        # compares against something real rather than a placeholder tile.
        cursor = await db.execute(
            f"SELECT p.id, p.name, p.topic, p.cefr_level, {thumb_subquery} AS thumb "
            "FROM projects p WHERE p.topic IS NOT NULL AND trim(p.topic) != '' "
            "ORDER BY (thumb IS NOT NULL) DESC, p.updated_at DESC LIMIT ?",
            (EPISODE_COUNT,),
        )
    episodes = [dict(row) for row in await cursor.fetchall()]
    if not episodes:
        raise SpikeError("no projects with a topic found in the database")
    for episode in episodes:
        episode["template_thumbnail"] = _template_thumbnail_path(episode)
    return episodes


def _template_thumbnail_path(episode: dict[str, Any]) -> str | None:
    if not episode.get("thumb"):
        return None
    row = {"project_id": episode["id"], "image_path_16x9": episode["thumb"], "image_path_9x16": episode["thumb"]}
    try:
        # The app's own resolver: same containment check (inside DATA_DIR/thumbnails/<id>).
        return str(_resolve_content_sync(row, "16x9", "png"))
    except NotFoundError:
        return None


def _subject_for(topic: str) -> str:
    topic = " ".join(topic.split())
    return f"illustration about {topic[:90]}"


# -- worker --------------------------------------------------------------------------


class _WorkerClient:
    def __init__(self, label: str, output_dir: Path, allow_cpu: bool) -> None:
        if not IMAGE_WORKER_PYTHON.is_file():
            raise SpikeError(
                f"{IMAGE_WORKER_PYTHON} not found -- set up venv-image first (see requirements-image.txt)"
            )
        self.stderr_log = output_dir / f"image_worker_{label}_stderr.log"
        command = [str(IMAGE_WORKER_PYTHON), str(IMAGE_WORKER_SCRIPT)]
        if allow_cpu:
            command.append("--allow-cpu")
        self._stderr_handle = open(self.stderr_log, "w", encoding="utf-8")
        self.process = subprocess.Popen(
            command, cwd=PROJECT_ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self._stderr_handle, text=True, encoding="utf-8", bufsize=1,
        )
        self.handshake = self._read_line()

    def _read_line(self) -> dict[str, Any]:
        assert self.process.stdout is not None
        line = self.process.stdout.readline()
        if not line:
            raise SpikeError(f"image_worker closed stdout unexpectedly (crashed?) -- see {self.stderr_log}")
        return json.loads(line)

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        return self._read_line()

    def close(self) -> None:
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=WORKER_EXIT_TIMEOUT_SECONDS)
        finally:
            self._stderr_handle.close()


def _checked(response: dict[str, Any], what: str) -> dict[str, Any]:
    if response.get("status") != "ok":
        raise SpikeError(f"{what} failed: {response.get('message', response)}")
    return response


def _run_candidate(
    mode: str, episodes: list[dict[str, Any]], output_dir: Path, args: argparse.Namespace
) -> dict[str, Any]:
    """One worker lifetime: load -> 5 backgrounds -> IP-Adapter sheet -> exit."""
    worker = _WorkerClient(mode, output_dir, args.allow_cpu)
    result: dict[str, Any] = {"handshake": worker.handshake, "images": [], "ip_adapter": None}
    try:
        if worker.handshake.get("status") != "ready":
            result["note"] = "worker refused to start (see handshake); no images"
            return result
        load_request: dict[str, Any] = {"command": "load", "mode": mode, "lightning_steps": 4,
                                        "vae_tiling": args.vae_tiling}
        if args.sources:
            load_request["sources"] = json.loads(Path(args.sources).read_text(encoding="utf-8"))
        result["load"] = _checked(worker.request(load_request), f"{mode} load")

        width, height = args.native_size
        for index, episode in enumerate(episodes):
            output_path = output_dir / f"ep{index + 1}_{mode}.png"
            response = _checked(worker.request({
                "command": "generate",
                "prompt": BACKGROUND_PROMPT.format(subject=_subject_for(episode["topic"])),
                "negative_prompt": NEGATIVE_PROMPT,
                "seed": EPISODE_SEED_BASE + index,
                "width": width, "height": height, "steps": args.base_steps,
                "output_path": str(output_path),
                "target_size": list(args.target_size),
            }), f"{mode} episode {index + 1}")
            result["images"].append({"episode_id": episode["id"], **response})

        if not args.skip_ip:
            result["ip_adapter"] = _run_ip_trial(worker, mode, output_dir, args)
        result["stats"] = worker.request({"command": "stats"})
        result["unload"] = worker.request({"command": "unload"})
    finally:
        worker.close()
    result["worker_exit_code"] = worker.process.returncode
    return result


def _run_ip_trial(worker: _WorkerClient, mode: str, output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    # The reference is generated BEFORE the adapter loads: once loaded, every call must
    # carry an ip_adapter_image (the worker enforces this).
    reference_path = output_dir / f"ip_reference_{mode}.png"
    reference = _checked(worker.request({
        "command": "generate", "prompt": REFERENCE_PROMPT, "negative_prompt": NEGATIVE_PROMPT,
        "seed": REFERENCE_SEED, "width": args.reference_size[0], "height": args.reference_size[1],
        "steps": args.base_steps, "output_path": str(reference_path),
    }), f"{mode} IP reference")
    adapter = _checked(worker.request({"command": "load_ip_adapter"}), f"{mode} load_ip_adapter")
    scenes = []
    width, height = args.native_size
    for scene_index, prompt in enumerate(SCENE_PROMPTS):
        for scale in IP_ADAPTER_SCALES:
            output_path = output_dir / f"ip_{mode}_scene{scene_index + 1}_s{int(scale * 10)}.png"
            response = _checked(worker.request({
                "command": "generate", "prompt": prompt, "negative_prompt": NEGATIVE_PROMPT,
                "seed": SCENE_SEED_BASE + scene_index, "width": width, "height": height,
                "steps": args.base_steps, "output_path": str(output_path),
                "ip_adapter_image": str(reference_path), "ip_adapter_scale": scale,
            }), f"{mode} IP scene {scene_index + 1} @ {scale}")
            scenes.append({"scene": scene_index + 1, "scale": scale, **response})
    return {"reference": reference, "load": adapter, "scenes": scenes}


# -- evidence ------------------------------------------------------------------------


async def _qwen_call(label: str) -> dict[str, Any]:
    """One real local qwen call with the app's own settings; returns timing or the error."""
    provider = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX
    )
    started = time.monotonic()
    try:
        result = await provider.generate(GenerationRequest(
            prompt="Reply with the single word OK.", deadline_seconds=300, purpose=f"spike_{label}",
        ))
    except ProviderError as exc:
        return {"label": label, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"label": label, "ok": True, "wall_sec": round(time.monotonic() - started, 3),
            "provider_latency_ms": round(result.latency_ms, 1), "num_ctx": settings.OLLAMA_NUM_CTX}


def _label_tile(image: Image.Image | None, size: tuple[int, int], label: str) -> Image.Image:
    tile = Image.new("RGB", (size[0], size[1] + 30), "white")
    if image is not None:
        tile.paste(ImageOps.fit(image.convert("RGB"), size, method=Image.Resampling.LANCZOS), (0, 30))
    else:
        ImageDraw.Draw(tile).rectangle((0, 30, size[0], size[1] + 30), fill=(230, 230, 230))
    ImageDraw.Draw(tile).text((8, 6), label, fill="black", font=ImageFont.load_default(size=18))
    return tile


def _open(path: str | None) -> Image.Image | None:
    if not path or not Path(path).is_file():
        return None
    with Image.open(path) as image:
        return image.copy()


def _sheet(rows: list[list[Image.Image]], output_path: Path) -> str:
    width = max(sum(tile.width for tile in row) for row in rows)
    height = sum(max(tile.height for tile in row) for row in rows)
    sheet = Image.new("RGB", (width, height), "white")
    y = 0
    for row in rows:
        x = 0
        for tile in row:
            sheet.paste(tile, (x, y))
            x += tile.width
        y += max(tile.height for tile in row)
    sheet.save(output_path, format="PNG")
    return str(output_path)


def _build_sheets(episodes: list[dict[str, Any]], candidates: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    tile = (640, 360)
    episode_sheets = []
    for index, episode in enumerate(episodes):
        row = [_label_tile(_open(episode["template_thumbnail"]), tile, "today (template)")]
        for mode, result in candidates.items():
            image_path = result["images"][index]["fitted_path"] if index < len(result.get("images", [])) else None
            row.append(_label_tile(_open(image_path), tile, mode))
        episode_sheets.append(_sheet([row], output_dir / f"sheet_ep{index + 1}.png"))

    ip_rows = []
    for mode, result in candidates.items():
        trial = result.get("ip_adapter")
        if not trial:
            continue
        row = [_label_tile(_open(trial["reference"]["output_path"]), (360, 360), f"{mode} reference")]
        for scene in trial["scenes"]:
            row.append(_label_tile(_open(scene["output_path"]), (480, 270), f"{mode} s{scene['scene']} @{scene['scale']}"))
        ip_rows.append(row)
    ip_sheet = _sheet(ip_rows, output_dir / "sheet_ip_adapter.png") if ip_rows else None
    return {"episodes": episode_sheets, "ip_adapter": ip_sheet}


# -- main ----------------------------------------------------------------------------


async def _main(args: argparse.Namespace) -> dict[str, Any]:
    db = await aiosqlite.connect(f"file:{settings.db_path.as_posix()}?mode=ro", uri=True)
    db.row_factory = aiosqlite.Row
    try:
        episodes = await _fetch_episodes(db, args.project_ids)
    finally:
        await db.close()

    output_dir = SPIKE_ROOT / f"run_{args.run_label}"
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "run_label": args.run_label,
        "episodes": [{k: e[k] for k in ("id", "name", "topic", "cefr_level", "template_thumbnail")} for e in episodes],
        "prompts": {"background": BACKGROUND_PROMPT, "negative": NEGATIVE_PROMPT,
                    "reference": REFERENCE_PROMPT, "scenes": list(SCENE_PROMPTS)},
        "gpu_snapshots": [_gpu_snapshot("start")],
        "qwen": [],
        "candidates": {},
    }

    if args.warm_qwen:
        report["qwen"].append(await _qwen_call("warm"))
        report["gpu_snapshots"].append(_gpu_snapshot("after_warm_qwen"))

    manager = get_gpu_manager()
    for mode in args.modes:
        if args.allow_cpu:
            # A CPU run needs no GPU lease; it only exists to exercise the plumbing.
            candidate = await asyncio.to_thread(_run_candidate, mode, episodes, output_dir, args)
            candidate["lease"] = "skipped (--allow-cpu run)"
        else:
            try:
                async with manager.lease(f"image_{mode}", min_free_mb=args.min_free_mb) as lease:
                    report["gpu_snapshots"].append(_gpu_snapshot(f"{mode}_lease_acquired"))
                    candidate = await asyncio.to_thread(_run_candidate, mode, episodes, output_dir, args)
                    report["gpu_snapshots"].append(_gpu_snapshot(f"{mode}_worker_exited"))
                candidate["lease"] = {
                    "min_free_mb": lease.min_free_mb, "waited_seconds": lease.waited_seconds,
                    "free_mb_before": lease.free_mb_before, "free_mb_after_eviction": lease.free_mb_after_eviction,
                    "evicted_models": lease.evicted_models,
                }
            except GpuUnavailableError as exc:
                # A real D20.1 outcome (the policy refusing), reported as data.
                candidate = {"lease": {"refused": exc.reason, "free_mb": exc.free_mb, "min_free_mb": exc.min_free_mb},
                             "images": []}
        report["candidates"][mode] = candidate

    if args.warm_qwen:
        report["qwen"].append(await _qwen_call("reload_after_eviction"))
        report["gpu_snapshots"].append(_gpu_snapshot("after_qwen_reload"))

    report["sheets"] = _build_sheets(episodes, report["candidates"], output_dir)
    report["output_dir"] = str(output_dir)
    return report


def _size(value: str) -> tuple[int, int]:
    width, _, height = value.lower().partition("x")
    return int(width), int(height)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task 20.2 image model spike runner")
    parser.add_argument("--run-label", default=time.strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--modes", nargs="+", choices=["base", "lightning"], default=["base", "lightning"])
    parser.add_argument("--project-ids", nargs="+", help="specific project ids instead of the 5 most recent")
    parser.add_argument("--warm-qwen", action="store_true",
                        help="make one real local qwen call first, so the first lease must evict it")
    parser.add_argument("--min-free-mb", type=int, default=PROVISIONAL_MIN_FREE_MB)
    parser.add_argument("--vae-tiling", action="store_true", help="mitigation if VAE decode runs out of VRAM")
    parser.add_argument("--skip-ip", action="store_true", help="backgrounds only, no IP-Adapter trial")
    parser.add_argument("--allow-cpu", action="store_true",
                        help="run the worker on CPU (plumbing check only -- real SDXL on CPU takes minutes per image)")
    parser.add_argument("--native-size", type=_size, default=(1344, 768), help="SDXL's nearest 16:9 bucket")
    parser.add_argument("--reference-size", type=_size, default=(1024, 1024))
    parser.add_argument("--target-size", type=_size, default=(1280, 720), help="the app's THUMBNAIL_*_16X9")
    parser.add_argument("--base-steps", type=int, default=30)
    parser.add_argument("--sources", help="JSON file of local model paths (offline mirror / plumbing tests)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_main(_parse_args())), indent=2))
