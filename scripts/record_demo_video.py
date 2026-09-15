"""Record a real screen-capture demo video of the full production pipeline.

Task 3.2 deliverable: "Demo video: Record full workflow from project creation to
YouTube package". Drives the actual running app (real Gemini, real Edge TTS, real
ffmpeg — nothing mocked, same "real, not mocked" standard as every other QA pass in this
project) with Playwright against a real in-process `uvicorn` server, using Playwright's
built-in video recording. No narration audio track — this is a silent screen capture of
real UI state changes, not a voiced-over marketing video.

Usage:
    venv\\Scripts\\python scripts\\record_demo_video.py
"""

from __future__ import annotations

import asyncio
import re
import shutil
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import uvicorn
from playwright.async_api import Page, async_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "docs" / "demo"
VIDEO_SIZE = {"width": 1440, "height": 900}
STEP_TIMEOUT_MS = 120_000
AUDIO_STEP_TIMEOUT_MS = 300_000  # sequential per-line real Edge TTS calls, slowest step


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _start_live_server() -> tuple[uvicorn.Server, str]:
    port = _find_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    started_at = time.time()
    while time.time() - started_at < 10.0:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Live demo server failed to start within 10 seconds")
    return server, f"http://127.0.0.1:{port}"


def _project_id_from_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    project_id = query.get("project_id", [None])[0]
    if not project_id:
        raise RuntimeError(f"Could not extract project_id from URL: {url}")
    return project_id


async def _create_project(page: Page, base_url: str) -> str:
    print("[step1] creating project...", flush=True)
    await page.goto(f"{base_url}/step1")
    await page.fill("#name", "Demo Episode")
    await page.fill("#topic", "The best way to start your morning")
    await page.select_option("#cefr", "B1")
    await page.click("#duration-presets button[data-minutes='5']")
    await page.click("#genre-grid button[data-value='small_talk']")
    await page.click("#accent-grid button[data-value='american']")
    await page.fill("#speaker-name-0", "Alex")
    await page.fill("#speaker-name-1", "Maya")
    async with page.expect_navigation(url=re.compile(r"/step2\?project_id="), timeout=STEP_TIMEOUT_MS):
        await page.click("#submit-btn")
    project_id = _project_id_from_url(page.url)
    print(f"[step1] project created: {project_id}", flush=True)
    return project_id


async def _run_step2_script(page: Page, base_url: str, project_id: str) -> None:
    print("[step2] generating script (real Gemini call)...", flush=True)
    await page.goto(f"{base_url}/step2?project_id={project_id}")
    await page.click("#generate-btn")
    await page.wait_for_selector("[data-line-id]", state="visible", timeout=STEP_TIMEOUT_MS)
    print("[step2] script generated", flush=True)


async def _run_step3_learning(page: Page, base_url: str, project_id: str) -> None:
    print("[step3] generating learning content (real Gemini call)...", flush=True)
    await page.goto(f"{base_url}/step3?project_id={project_id}")
    await page.click("#generate-btn")
    await page.wait_for_selector("#content-wrap", state="visible", timeout=STEP_TIMEOUT_MS)
    print("[step3] learning content generated", flush=True)


async def _run_step4_audio(page: Page, base_url: str, project_id: str) -> None:
    print("[step4] synthesizing + mixing audio (real Edge TTS + ffmpeg)...", flush=True)
    await page.goto(f"{base_url}/step4?project_id={project_id}")
    await page.wait_for_selector("#workspace", state="visible", timeout=STEP_TIMEOUT_MS)
    await page.click("#generate-btn")
    try:
        await page.wait_for_selector("#result-card", state="visible", timeout=AUDIO_STEP_TIMEOUT_MS)
    except Exception:
        error_text = await page.locator("#error-banner").text_content()
        progress_text = await page.locator("#generate-progress").text_content()
        print(f"[step4] FAILED — error banner: {error_text!r}, progress: {progress_text!r}", flush=True)
        raise
    print("[step4] audio mix complete", flush=True)


async def _run_step5_video(page: Page, base_url: str, project_id: str) -> None:
    print("[step5] rendering video (real ffmpeg)...", flush=True)
    await page.goto(f"{base_url}/step5?project_id={project_id}")
    await page.wait_for_selector("#workspace", state="visible", timeout=STEP_TIMEOUT_MS)
    await page.click("#generate-btn")
    await page.wait_for_selector("#result-card", state="visible", timeout=STEP_TIMEOUT_MS)
    print("[step5] video rendered", flush=True)


async def _run_step6_thumbnail(page: Page, base_url: str, project_id: str) -> None:
    print("[step6] generating thumbnails (real Gemini + Pillow)...", flush=True)
    await page.goto(f"{base_url}/step6?project_id={project_id}")
    await page.wait_for_selector("#workspace", state="visible", timeout=STEP_TIMEOUT_MS)
    await page.click("#generate-btn")
    await page.wait_for_function(
        "document.querySelector('#variant-grid').children.length > 0", timeout=STEP_TIMEOUT_MS
    )
    print("[step6] thumbnails generated", flush=True)


async def _run_step7_youtube(page: Page, base_url: str, project_id: str) -> None:
    print("[step7] generating YouTube package (real Gemini call)...", flush=True)
    await page.goto(f"{base_url}/step7?project_id={project_id}")
    await page.click("#generate-btn")
    await page.wait_for_selector("#content-wrap", state="visible", timeout=STEP_TIMEOUT_MS)
    print("[step7] YouTube package generated", flush=True)
    await page.wait_for_timeout(2000)  # let the final frame linger in the recording


async def main_async() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server, base_url = _start_live_server()
    started_at = time.monotonic()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIDEO_SIZE,
            record_video_dir=str(OUTPUT_DIR),
            record_video_size=VIDEO_SIZE,
        )
        page = await context.new_page()
        try:
            project_id = await _create_project(page, base_url)
            await _run_step2_script(page, base_url, project_id)
            await _run_step3_learning(page, base_url, project_id)
            await _run_step4_audio(page, base_url, project_id)
            await _run_step5_video(page, base_url, project_id)
            await _run_step6_thumbnail(page, base_url, project_id)
            await _run_step7_youtube(page, base_url, project_id)
        finally:
            video = page.video
            await context.close()
            await browser.close()
            if video is not None:
                recorded_path = Path(await video.path())
                final_path = OUTPUT_DIR / "demo-video.webm"
                shutil.move(str(recorded_path), final_path)
                print(f"Video saved: {final_path}", flush=True)

    duration = time.monotonic() - started_at
    print(f"Total wall-clock time: {duration:.1f}s", flush=True)
    server.should_exit = True
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
