"""Run the Phase 33 owner-workflow rehearsal against an explicitly marked data copy.

The script starts the real app, drives the Character Library with Playwright, creates
and locks a third profile, builds a three-speaker project, and renders the two owner
acceptance modes with Remotion.  It refuses any data directory without the marker
created for this rehearsal.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.async_api import APIResponse, Page, async_playwright

ROOT = Path(__file__).resolve().parents[1]
MARKER = ".phase33-acceptance-copy"
OLD_PROJECT_ID = "b330d37f-a212-4cf7-a779-7a109098bd6c"
CORE_SLOTS = ("face", "full_body", "portrait_calm", "portrait_smile", "portrait_surprised")
TIER_1_SLOTS = (
    "calm__closed", "calm__open", "smile__closed", "smile__open",
    "surprised__closed", "surprised__open", "blink",
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _assert_copy(data_dir: Path) -> None:
    data_dir = data_dir.resolve()
    if not (data_dir / MARKER).is_file() or not (data_dir / "app.db").is_file():
        raise ValueError(f"Refusing unmarked data directory: expected {MARKER} and app.db in {data_dir}")


def _copy_file(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        return destination.resolve()
    shutil.copy2(source, destination)
    return destination.resolve()


def prepare_isolated_media(data_dir: Path, source_data_dir: Path) -> dict:
    """Rebase copied rows and copy only media needed by the acceptance renders."""
    database = data_dir / "app.db"
    changes = {"character_assets_rebased": 0, "copied": []}
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT id, path FROM character_assets").fetchall()
        for row in rows:
            raw = Path(row["path"])
            parts = list(raw.parts)
            try:
                library_at = next(index for index, part in enumerate(parts) if part.lower() == "library")
            except StopIteration:
                continue
            candidate = data_dir.joinpath(*parts[library_at:]).resolve()
            if candidate.is_file() and str(candidate) != row["path"]:
                connection.execute("UPDATE character_assets SET path = ? WHERE id = ?", (str(candidate), row["id"]))
                changes["character_assets_rebased"] += 1

        scene_id = "builtin-kitchen"
        scene = connection.execute("SELECT preview_path FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        scene_source = Path(scene["preview_path"]) if scene and scene["preview_path"] else Path()
        if not scene_source.is_file():
            scene_source = source_data_dir / "library" / "scenes" / scene_id / "preview.png"
        scene_copy = _copy_file(scene_source, data_dir / "library" / "scenes" / scene_id / "preview.png")
        connection.execute("UPDATE scenes SET preview_path = ? WHERE id = ?", (str(scene_copy), scene_id))
        changes["copied"].append(str(scene_copy))

        activity = connection.execute(
            "SELECT id, path FROM activity_library WHERE review_state = 'approved' AND activity = 'cooking' "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if activity is None:
            raise ValueError("The copied database has no approved generic 'cooking' activity")
        activity_source = Path(activity["path"])
        if not activity_source.is_file():
            activity_source = source_data_dir / "library" / "activities" / f"{activity['id']}.png"
        activity_copy = _copy_file(
            activity_source, data_dir / "library" / "activities" / f"{activity['id']}.png"
        )
        connection.execute("UPDATE activity_library SET path = ? WHERE id = ?", (str(activity_copy), activity["id"]))
        changes["copied"].append(str(activity_copy))

        old_audio = connection.execute(
            "SELECT mp3_path, wav_path FROM audio_jobs WHERE project_id = ? AND status = 'complete'",
            (OLD_PROJECT_ID,),
        ).fetchone()
        if old_audio:
            output = data_dir / "audio" / OLD_PROJECT_ID
            mp3 = _copy_file(source_data_dir / "audio" / OLD_PROJECT_ID / "mix.mp3", output / "mix.mp3")
            wav = _copy_file(source_data_dir / "audio" / OLD_PROJECT_ID / "mix.wav", output / "mix.wav")
            voice_source = source_data_dir / "audio" / OLD_PROJECT_ID / "voice.wav"
            if voice_source.is_file():
                changes["copied"].append(str(_copy_file(voice_source, output / "voice.wav")))
            connection.execute(
                "UPDATE audio_jobs SET mp3_path = ?, wav_path = ? WHERE project_id = ?",
                (str(mp3), str(wav), OLD_PROJECT_ID),
            )
            changes["copied"].extend((str(mp3), str(wav)))
        connection.commit()
    return changes


def generate_inputs(folder: Path) -> dict[str, Path]:
    """Create deterministic external-upload fixtures that satisfy every slot contract."""
    folder.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    core_sizes = {
        "face": (512, 512), "full_body": (640, 960),
        "portrait_calm": (512, 512), "portrait_smile": (512, 512),
        "portrait_surprised": (512, 512),
    }
    for index, (slot, size) in enumerate(core_sizes.items()):
        image = Image.new("RGB", size, (230 - index * 12, 238, 246 - index * 8))
        draw = ImageDraw.Draw(image)
        width, height = size
        draw.ellipse((width * 0.32, height * 0.10, width * 0.68, height * 0.43), fill=(202, 145, 112))
        draw.rectangle((width * 0.23, height * 0.43, width * 0.77, height * 0.94), fill=(55, 112, 92))
        draw.text((18, 18), f"Rowan / {slot}", fill=(20, 35, 45))
        path = folder / f"rowan-{slot}.png"
        image.save(path)
        files[slot] = path
    for index, slot in enumerate(TIER_1_SLOTS):
        image = Image.new("RGBA", (1280, 1536), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((500, 200, 780, 520), fill=(202, 145, 112, 255))
        draw.rectangle((380, 520, 900, 1535), fill=(55, 112, 92, 255))
        eye_y = 315 if slot != "blink" else 330
        draw.line((565, eye_y, 605, eye_y), fill=(30, 25, 25, 255), width=8)
        draw.line((675, eye_y, 715, eye_y), fill=(30, 25, 25, 255), width=8)
        mouth_open = slot.endswith("__open")
        if mouth_open:
            draw.ellipse((610, 405, 670, 455), fill=(80, 25, 35, 255))
        else:
            draw.line((610, 430, 670, 430), fill=(80, 25, 35, 255), width=8)
        path = folder / f"rowan-{slot}.png"
        image.save(path)
        files[slot] = path
    return files


async def _json(response: APIResponse) -> dict:
    payload = await response.json()
    if not response.ok or not payload.get("success"):
        raise RuntimeError(f"{response.request.method} {response.url}: {response.status} {payload}")
    return payload["data"]


async def _upload_group(page: Page, files: dict[str, Path], slots: tuple[str, ...]) -> None:
    await page.locator("#asset-bulk-input").set_input_files([str(files[slot]) for slot in slots])
    items = page.locator(".bulk-map-item")
    if await items.count() != len(slots):
        raise AssertionError("Asset Studio did not keep every selected preview visible")
    for index, slot in enumerate(slots):
        await items.nth(index).locator("select").select_option(slot)
    await page.locator("#asset-bulk-upload").click()
    await page.get_by_text(f"{len(slots)} pictures uploaded. Review them below.").wait_for(timeout=120_000)
    for slot_index in range(len(slots)):
        cards = page.locator(".asset-slot-card")
        button = cards.nth(slot_index).get_by_role("button", name="Approve")
        await button.click()
        await cards.nth(slot_index).get_by_text("Ready").wait_for(timeout=30_000)


async def _create_rowan(page: Page, base_url: str, inputs: dict[str, Path], evidence: Path) -> dict:
    await page.goto(f"{base_url}/characters")
    await page.locator("#new-character").click()
    await page.locator("#wizard-next").click()
    form = page.locator("#character-wizard-form")
    await form.locator('[name="name"]').fill("Rowan")
    await form.locator('[name="role"]').fill("Travel guide")
    await form.locator('[name="intro"]').fill("A practical guide who helps learners handle everyday travel conversations.")
    await page.locator("#wizard-next").click()
    await form.locator('[name="personality"]').fill("calm, observant, helpful")
    await form.locator('[name="speaking_style"]').fill("clear and practical")
    await form.locator('[name="dialogue_behavior"]').fill("Invites both partners into the conversation and gives short examples.")
    await page.locator("#wizard-next").click()
    await form.locator('[name="gender"]').select_option("female")
    await form.locator('[name="age_group"]').select_option("adult")
    await form.locator('[name="ethnicity"]').fill("Vietnamese")
    await form.locator('[name="hair"]').fill("short black hair")
    await form.locator('[name="eyes"]').fill("brown eyes")
    await form.locator('[name="extra"]').fill("round glasses")
    await form.locator('[name="top_color"]').select_option("green")
    await form.locator('[name="top_item"]').select_option("shirt")
    await form.locator('[name="bottom_color"]').select_option("beige")
    await form.locator('[name="bottom_item"]').select_option("trousers")
    await page.locator("#wizard-next").click()
    await form.locator('[name="default_accent"]').fill("british")
    await form.locator('[name="default_voice_id"]').fill("en-GB-SoniaNeural")
    await form.locator('[name="default_speed"]').fill("0.95")
    await form.locator('[name="default_voice_description"]').fill("Warm, composed adult guide")
    await page.locator("#wizard-next").click()
    await page.get_by_role("heading", name="Identity references").wait_for()

    # A fresh browser context proves wizard progress is persisted in the database.
    browser = page.context.browser
    if browser is None:
        raise RuntimeError("Playwright browser closed unexpectedly")
    await page.context.close()
    context = await browser.new_context(viewport={"width": 1440, "height": 1000})
    page = await context.new_page()
    await page.goto(f"{base_url}/characters")
    await page.get_by_role("button", name="Rowan, Travel guide").click()
    await page.locator("#resume-character").click()
    await page.get_by_role("heading", name="Identity references").wait_for()

    await page.get_by_role("button", name="Open Visual Asset Studio").click()
    await _upload_group(page, inputs, CORE_SLOTS)
    await page.screenshot(path=evidence / "01-rowan-core-approved.png", full_page=True)
    await page.locator("#asset-studio-close").click()
    await page.locator("#wizard-next").click()
    await page.locator("#wizard-next").click()
    await page.get_by_role("button", name="Add starter sprites").click()
    await _upload_group(page, inputs, TIER_1_SLOTS)
    await page.screenshot(path=evidence / "02-rowan-talking-starter-approved.png", full_page=True)
    await page.locator("#asset-studio-close").click()
    await page.locator("#wizard-next").click()
    await page.locator("#wizard-skip").click()
    await page.locator("#wizard-skip").click()
    await page.locator("#wizard-next").click()
    await page.locator("#legacy-character-tools summary").click()
    await page.locator("#lock-character").wait_for(state="visible")
    await page.locator("#lock-character").click()
    await page.locator("#unlock-character").wait_for()
    await page.screenshot(path=evidence / "03-rowan-locked-profile.png", full_page=True)
    profiles = await _json(await page.request.get(f"{base_url}/api/visuals/characters"))
    rowan = next(item for item in profiles if item["name"] == "Rowan")
    return {"page": page, "profile": rowan}


async def _build_project(page: Page, base_url: str, profiles: list[dict], evidence: Path) -> tuple[dict, list[dict]]:
    by_name = {profile["name"]: profile for profile in profiles}
    for name, patch in {
        "Alex": {"default_accent": "american", "default_voice_id": "en-US-GuyNeural", "default_voice_description": "Direct adult male voice"},
        "Lina": {"default_accent": "american", "default_voice_id": "en-US-JennyNeural", "default_voice_description": "Warm adult female voice"},
    }.items():
        await _json(await page.request.patch(
            f"{base_url}/api/visuals/characters/{by_name[name]['id']}", data=patch
        ))
    project = await _json(await page.request.post(f"{base_url}/api/projects", data={
        "name": "Phase 33 three character acceptance", "topic": "Planning a simple food tour",
        "cefr_level": "B1", "duration_minutes": 1, "num_speakers": 3,
        "genre": "small_talk", "accent": "american",
        "speakers": [
            {"name": "Custom Alex", "gender": "male", "accent": "american", "tts_engine": "edge_tts", "voice_id": "en-US-GuyNeural", "speed": 1.1},
            {"name": "Host two", "gender": "female", "accent": "american", "tts_engine": "edge_tts"},
            {"name": "Guest three", "gender": "female", "accent": "british", "tts_engine": "edge_tts"},
        ],
    }))
    speaker_ids = [speaker["id"] for speaker in sorted(project["speakers"], key=lambda item: item["speaker_index"])]
    texts = (
        "Let us plan a short food tour for Saturday.",
        "Great, I would like one quiet place to start.",
        "I can guide us through the market and explain what to try.",
        "While we are cooking, we can compare the local flavours.",
        "Then Alex and Rowan can choose the final stop together.",
        "Perfect, everyone has a clear part in the plan.",
    )
    lines = await _json(await page.request.put(f"{base_url}/api/projects/{project['id']}/script", data={
        "lines": [{"speaker_id": speaker_ids[index % 3], "text": text} for index, text in enumerate(texts)]
    }))
    for line in lines:
        await _json(await page.request.post(
            f"{base_url}/api/projects/{project['id']}/tts/preview", data={"line_id": line["id"]}, timeout=120_000
        ))
    await _json(await page.request.post(f"{base_url}/api/projects/{project['id']}/audio/generate", data={}, timeout=180_000))

    await page.goto(f"{base_url}/step5?project_id={project['id']}")
    await page.locator(".cast-roster-card").first.wait_for(timeout=60_000)
    for index, name in enumerate(("Alex", "Lina", "Rowan")):
        await page.locator(f'[data-cast-speaker-index="{index}"]').click()
        await page.locator(f'[data-character-id="{by_name[name]["id"]}"]').click()
        copy = page.locator("#cast-copy-profile-defaults")
        if index == 0:
            await copy.uncheck()
        else:
            await copy.check()
        await page.locator('[data-action="choose-profile"]').click()
        await page.wait_for_function(
            "([slot, name]) => document.querySelector(`[data-cast-speaker-index=\"${slot}\"] span`).textContent.includes(name)",
            arg=[index, name],
        )
    await page.request.put(f"{base_url}/api/projects/{project['id']}/visuals/scenes", data=["builtin-kitchen"])
    storyboard = await _json(await page.request.put(f"{base_url}/api/projects/{project['id']}/storyboard", data={
        "status": "approved", "beats": [
            {"line_from": 0, "line_to": 1, "kind": "scene", "scene_id": "builtin-kitchen", "speakers": [0, 1], "action": "planning a food tour", "expression": "smile"},
            {"line_from": 2, "line_to": 3, "kind": "insert", "speakers": [2], "action": "cooking", "expression": "calm"},
            {"line_from": 4, "line_to": 5, "kind": "scene", "scene_id": "builtin-kitchen", "speakers": [0, 2], "action": "sharing ideas", "expression": "smile"},
        ],
    }))
    await page.reload()
    await page.locator(".cast-roster-card").first.wait_for(timeout=60_000)
    await page.screenshot(path=evidence / "04-three-character-selector.png", full_page=True)
    return project, storyboard["beats"]


async def _render(page: Page, base_url: str, project_id: str, mode: str, destination: Path) -> dict:
    subtitle = destination.with_suffix(".srt")
    subtitle.unlink(missing_ok=True)
    job = await _json(await page.request.post(
        f"{base_url}/api/projects/{project_id}/video/generate",
        data={"template_id": "midnight", "renderer": "remotion", "caption_style": "outline",
              "visual_mode": mode, "still_scene_id": "builtin-kitchen"},
        timeout=700_000,
    ))
    if job.get("fallback_used") or job.get("mode") != "remotion":
        raise RuntimeError(f"Remotion acceptance render fell back: {job}")
    _copy_file(Path(job["mp4_path"]), destination)
    if job.get("srt_path") and Path(job["srt_path"]).is_file():
        _copy_file(Path(job["srt_path"]), subtitle)
    return job


async def run(args: argparse.Namespace) -> dict:
    data_dir, source_data_dir, evidence = args.data_dir.resolve(), args.source_data_dir.resolve(), args.evidence_dir.resolve()
    _assert_copy(data_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    prep = prepare_isolated_media(data_dir, source_data_dir)
    inputs = generate_inputs(evidence / "external-inputs")
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment.update({"DIE_DATA_DIR": str(data_dir), "DIE_VIDEO_RENDERER": "remotion"})
    log_path = evidence / "server.log"
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(120):
                try:
                    with urllib.request.urlopen(f"{base_url}/api/projects", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    await asyncio.sleep(0.25)
            else:
                raise RuntimeError(f"App did not start; see {log_path}")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(viewport={"width": 1440, "height": 1000})
                page = await context.new_page()
                created = await _create_rowan(page, base_url, inputs, evidence)
                page, rowan = created["page"], created["profile"]
                profiles = await _json(await page.request.get(f"{base_url}/api/visuals/characters"))
                project, beats = await _build_project(page, base_url, profiles, evidence)
                still = await _render(page, base_url, project["id"], "podcast_still", evidence / "phase33-three-cast-still.mp4")
                sprites = await _render(page, base_url, project["id"], "podcast_sprites", evidence / "phase33-three-cast-talking.mp4")
                old = await _render(page, base_url, OLD_PROJECT_ID, "podcast_still", evidence / "phase33-old-alex-lina.mp4")
                final_project = await _json(await page.request.get(f"{base_url}/api/projects/{project['id']}"))
                visuals = await _json(await page.request.get(f"{base_url}/api/projects/{project['id']}/visuals"))
                coverage = await _json(await page.request.get(f"{base_url}/api/projects/{project['id']}/visuals/activity-coverage"))
                await browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
    report = {
        "ok": True, "duration_seconds": round(time.monotonic() - started, 2), "data_dir": str(data_dir),
        "media_preparation": prep, "rowan_id": rowan["id"], "rowan_status": rowan["status"],
        "rowan_readiness": rowan["readiness"], "project_id": project["id"],
        "speakers": final_project["speakers"], "cast": visuals["cast"], "storyboard_beats": beats,
        "activity_coverage": coverage, "renders": {"still": still, "talking": sprites, "old_project": old},
    }
    (evidence / "acceptance-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--source-data-dir", type=Path, required=True, help="Read-only source for media copied into rehearsal data")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = asyncio.run(run(args))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
