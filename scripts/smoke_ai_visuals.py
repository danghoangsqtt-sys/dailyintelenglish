r"""Isolated Phase 20 end-to-end smoke through the API and Remotion still renderer.

Usage:
    venv\Scripts\python scripts\smoke_ai_visuals.py --fake
    venv\Scripts\python scripts\smoke_ai_visuals.py --output-dir data\tmp\gate-b14 --duo-refine on --seed 20261001

With --output-dir the run keeps, besides the three Remotion stills, every shot's raw and final
image, both characters' candidates/face/sheet, and `contact_shots.png` (raw | final per shot), so
Gate B-14 can judge the duo refine and compare `--duo-refine on` vs `off` at the same seed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pydub.generators import Sine

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import video_renderer_remotion  # noqa: E402


def api(client: TestClient, method: str, path: str, body: object | None = None):
    response = client.request(method, path, json=body)
    if response.status_code != 200:
        raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {response.text[:500]}")
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"{method} {path}: {payload}")
    return payload["data"]


def wait_job(client: TestClient, job: dict, label: str, timeout: float = 7200) -> dict:
    deadline = time.monotonic() + timeout
    last_stage = None
    while time.monotonic() < deadline:
        current = api(client, "GET", f"/api/visuals/jobs/{job['id']}")
        stage = (current["status"], current["stage"], current["progress"])
        if stage != last_stage:
            print(f"{label}: {stage[0]} — {stage[1]} ({stage[2]}%)", flush=True)
            last_stage = stage
        if current["status"] == "complete":
            return current
        if current["status"] in ("error", "cancelled"):
            raise RuntimeError(f"{label}: {current['status']}: {current['error']}")
        time.sleep(0.5)
    raise TimeoutError(f"{label} exceeded {timeout:g} seconds")


# The owner's accepted r8 pair (20.2h): the female student unchanged, the male neat and slim-fit.
CHARACTERS = {
    "female": {"hair": "long black hair", "top_color": "yellow", "top_item": "sweater",
               "bottom_color": "navy blue", "bottom_item": "jeans"},
    "male": {"hair": "short neat black hair", "top_color": "light blue", "top_item": "slim-fit shirt",
             "bottom_color": "black", "bottom_item": "slim trousers"},
}


def create_locked_character(client: TestClient, name: str, gender: str) -> str:
    descriptor = {
        "name": name, "gender": gender, "age_group": "young", "ethnicity": "Vietnamese",
        "role": "university student", "eyes": "brown eyes", **CHARACTERS[gender],
    }
    character = api(client, "POST", "/api/visuals/characters", descriptor)
    character_id = character["id"]
    base = f"/api/visuals/characters/{character_id}"
    wait_job(client, api(client, "POST", f"{base}/candidates"), f"{name} candidates")
    character = api(client, "GET", base)
    candidate = next(asset for asset in character["assets"] if asset["kind"] == "candidate")
    api(client, "PUT", f"{base}/reference", {"asset_id": candidate["id"]})
    wait_job(client, api(client, "POST", f"{base}/sheet", []), f"{name} sheet")
    character = api(client, "GET", base)
    sheet = [asset for asset in character["assets"] if asset["kind"] in
             ("full_body", "portrait_calm", "portrait_smile", "portrait_surprised")]
    if len(sheet) != 4:
        raise RuntimeError(f"{name}: expected four sheet assets, got {len(sheet)}")
    for asset in sheet:
        api(client, "PUT", f"{base}/assets/{asset['id']}/approve", {"approved": True})
    locked = api(client, "POST", f"{base}/lock")
    if locked["status"] != "locked":
        raise RuntimeError(f"{name}: lock did not complete")
    return character_id


async def build_props(project: dict, audio_job: dict) -> dict:
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        return await video_renderer_remotion._build_input_props(db, project, audio_job, None)


def render_stills(project: dict, shots: list[dict], work_dir: Path, output_dir: Path) -> list[str]:
    audio_source = work_dir / "smoke.mp3"
    Sine(440).to_audio_segment(duration=4000).apply_gain(-25).export(
        str(audio_source), format="mp3", bitrate="128k",
    )
    entries = []
    for index in range(4):
        speaker = project["speakers"][index % 2]
        entries.append({"start_sec": float(index), "end_sec": float(index + 1),
                        "label": speaker["name"], "speaker_id": speaker["id"], "text": "A short lesson line."})
    audio_job = {"mp3_path": str(audio_source), "timestamps": entries, "word_timestamps": []}
    props = asyncio.run(build_props(project, audio_job))
    if len(props.get("visuals", {}).get("shots", {})) != len(shots):
        raise RuntimeError("Remotion props did not include every complete shot")
    video_renderer_remotion._copy_audio_into_public(project["id"], str(audio_source))
    npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    output_dir.mkdir(parents=True, exist_ok=True)
    stills = []
    try:
        for kind in ("single", "duo_close", "duo_wide"):
            shot = next(shot for shot in shots if shot["kind"] == kind)
            shot_props = {**props, "visuals": {
                **props["visuals"], "lineShots": [shot["id"]] * len(entries),
            }}
            props_path = work_dir / f"{kind}_props.json"
            props_path.write_text(json.dumps(shot_props), encoding="utf-8")
            output = output_dir / f"{kind}.png"
            command = [npx, "remotion", "still", "src/index.ts", "StillFrame", str(output),
                       f"--props={props_path}", "--frame=15"]
            print(f"Remotion still: {kind}", flush=True)
            result = subprocess.run(command, cwd=video_renderer_remotion.VIDEO_RENDERER_DIR,
                                    capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"Remotion {kind} failed: {result.stderr[-1000:]}")
            with Image.open(output) as image:
                if image.size != (1280, 720):
                    raise RuntimeError(f"Remotion {kind} still has wrong dimensions: {image.size}")
            stills.append(str(output))
    finally:
        public_visuals = video_renderer_remotion.REMOTION_VISUALS_DIR.resolve()
        project_visuals = (public_visuals / project["id"]).resolve()
        if project_visuals.is_relative_to(public_visuals) and project_visuals != public_visuals:
            shutil.rmtree(project_visuals, ignore_errors=True)
        (video_renderer_remotion.REMOTION_AUDIO_DIR / f"{project['id']}.mp3").unlink(missing_ok=True)
        for speaker in project["speakers"]:
            (video_renderer_remotion.REMOTION_AVATARS_DIR / f"{speaker['id']}_cast.png").unlink(missing_ok=True)
    return stills


def _thumb(path: Path, width: int) -> Image.Image:
    with Image.open(path) as image:
        image = image.convert("RGB")
        return image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)


def keep_evidence(client: TestClient, characters: dict[str, str], project_id: str, shots: list[dict],
                  scenes: list[dict], data_dir: Path, output_dir: Path) -> dict:
    """Copy the library and shot images out of the temporary data dir before it is deleted."""
    kept = {"characters": [], "shots": []}
    for name, character_id in characters.items():
        character = api(client, "GET", f"/api/visuals/characters/{character_id}")
        source_dir = data_dir / "library" / "characters" / character_id
        target_dir = output_dir / "characters" / name
        for path in sorted(source_dir.rglob("*.png")):
            target = target_dir / path.relative_to(source_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        kept["characters"].append({"name": name, "status": character["status"],
                                   "reference_asset_id": character["reference_asset_id"]})
    scene_names = {scene["id"]: scene["name"] for scene in scenes}
    rows = []
    for index, shot in enumerate(shots):
        folder = data_dir / "visuals" / project_id / "shots" / shot["id"]
        label = f"{index:02d}_{scene_names.get(shot['scene_id'], 'scene')}_{shot['kind']}_" + \
            "-".join(str(i) for i in shot["speaker_indexes"])
        pair = []
        for variant in ("raw", "final"):
            source = folder / f"{variant}.png"
            if source.is_file():
                target = output_dir / "shots" / f"{label}_{variant}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                pair.append(target)
        kept["shots"].append({"label": label, "seed": shot["seed"], "prompt_tokens": shot["prompt_tokens"],
                              "prompt_truncated": bool(shot["prompt_truncated"])})
        if len(pair) == 2:
            rows.append((label, pair))
    if rows:
        width, gap, caption = 640, 8, 22
        height = _thumb(rows[0][1][0], width).height
        sheet = Image.new("RGB", (2 * width + 3 * gap, len(rows) * (height + caption + gap) + gap), "white")
        draw = ImageDraw.Draw(sheet)
        for row, (label, (raw, final)) in enumerate(rows):
            top = gap + row * (height + caption + gap)
            draw.text((gap, top), f"{label}   raw | final", fill="black")
            sheet.paste(_thumb(raw, width), (gap, top + caption))
            sheet.paste(_thumb(final, width), (2 * gap + width, top + caption))
        sheet.save(output_dir / "contact_shots.png")
    return kept


def smoke(fake: bool, output_root: Path | None, duo_refine: bool = True, seed: int | None = None) -> dict:
    if seed is not None:
        random.seed(seed)  # character base seeds and shot seeds -> refine on/off runs are comparable
    with tempfile.TemporaryDirectory(prefix="die-ai-visuals-") as temporary:
        work_dir = Path(temporary)
        data_dir = work_dir / "data"
        os.environ["DIE_DATA_DIR"] = str(data_dir)
        os.environ["DIE_IMAGE_ENGINE"] = "fake" if fake else "worker"
        os.environ["DIE_AI_VISUALS_ENABLED"] = "true"
        settings.DATA_DIR = data_dir
        settings.IMAGE_ENGINE = "fake" if fake else "worker"
        settings.AI_VISUALS_ENABLED = True
        settings.VISUALS_DUO_REFINE = duo_refine
        with TestClient(app) as client:
            first = create_locked_character(client, "Lan", "female")
            second = create_locked_character(client, "Minh", "male")
            project = api(client, "POST", "/api/projects", {
                "name": "Conversation lesson", "topic": "Meeting at a cafe", "cefr_level": "B1",
                "duration_minutes": 2, "num_speakers": 2, "genre": "small_talk", "accent": "american",
                "speakers": [{"name": "Lan", "gender": "female", "accent": "american"},
                             {"name": "Minh", "gender": "male", "accent": "american"}],
            })
            project_id = project["id"]
            base = f"/api/projects/{project_id}/visuals"
            api(client, "PUT", f"{base}/cast", [
                {"speaker_index": 0, "character_id": first},
                {"speaker_index": 1, "character_id": second},
            ])
            scenes = api(client, "GET", "/api/visuals/scenes")[:2]
            api(client, "PUT", f"{base}/scenes", [scene["id"] for scene in scenes])
            shots_started = time.monotonic()
            wait_job(client, api(client, "POST", f"{base}/shots"), "project shots")
            shots_seconds = round(time.monotonic() - shots_started, 2)
            shots = api(client, "GET", base)["shots"]
            if len(shots) != 8 or {shot["kind"] for shot in shots} != {"single", "duo_close", "duo_wide"}:
                raise RuntimeError(f"Expected eight shots of all three kinds, got {shots}")
            if any(shot["status"] != "complete" or not shot["final_url"] for shot in shots):
                raise RuntimeError("A project shot is incomplete")
            if output_root:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                output_dir = output_root.resolve() / f"{stamp}-{project_id[:8]}"
            else:
                output_dir = work_dir / "stills"
            stills_started = time.monotonic()
            stills = render_stills(project, shots, work_dir, output_dir)
            stills_seconds = round(time.monotonic() - stills_started, 2)
            evidence = (keep_evidence(client, {"Lan": first, "Minh": second}, project_id, shots, scenes,
                                      data_dir, output_dir) if output_root else None)
            result = {"engine": settings.IMAGE_ENGINE, "duo_refine": duo_refine, "seed": seed,
                      "project_id": project_id, "output_dir": str(output_dir) if output_root else None,
                      "evidence": evidence,
                      "characters": [first, second], "scenes": [scene["id"] for scene in scenes],
                      "shot_count": len(shots), "shot_generation_seconds": shots_seconds,
                      "three_stills_seconds": stills_seconds, "stills": stills}
            print(json.dumps(result, indent=2), flush=True)
            return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fake", action="store_true", help="Use deterministic images without GPU")
    parser.add_argument("--output-dir", type=Path,
                        help="Keep the stills, raw/final shots, character images and contact sheet here")
    parser.add_argument("--duo-refine", choices=("on", "off"), default="on",
                        help="Spec 2.7 regional refine for duo shots (Gate B-14 compares on vs off)")
    parser.add_argument("--seed", type=int, help="Seed the run so on/off comparisons use the same seeds")
    args = parser.parse_args()
    try:
        smoke(args.fake, args.output_dir, args.duo_refine == "on", args.seed)
    except Exception as exc:
        print(f"AI visuals smoke failed: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
