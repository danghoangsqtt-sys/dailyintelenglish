"""Browser coverage for Task 4.2c's Video Studio shell and timeline."""

import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "video-shell-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "Video Shell Test",
    "status": "audio_generated",
    "cefr_level": "B1",
    "genre": "interview",
    "speakers": [
        {
            "id": "speaker-a",
            "name": "Alex",
            "gender": "male",
            "accent": "american",
            "tts_engine": "edge_tts",
            "avatar_image_path": None,
        },
        {
            "id": "speaker-b",
            "name": "Sam",
            "gender": "female",
            "accent": "british",
            "tts_engine": "edge_tts",
            "avatar_image_path": None,
        },
    ],
}
LINES = [
    {
        "id": "line-1",
        "line_index": 0,
        "speaker_id": "speaker-a",
        "text": "Welcome to today's discussion.",
        "language_notes": None,
        "duration_seconds": None,
    },
    {
        "id": "line-2",
        "line_index": 1,
        "speaker_id": "speaker-b",
        "text": "Let's look at the evidence.",
        "language_notes": None,
        "duration_seconds": None,
    },
    {
        "id": "line-3",
        "line_index": 2,
        "speaker_id": "speaker-a",
        "text": "That brings us to the conclusion.",
        "language_notes": None,
        "duration_seconds": None,
    },
]
AUDIO_JOB = {
    "project_id": PROJECT_ID,
    "status": "complete",
    "mp3_path": f"data/audio/{PROJECT_ID}/mix.mp3",
    "wav_path": f"data/audio/{PROJECT_ID}/mix.wav",
    "timestamps": [
        {"start_sec": 0.4, "end_sec": 2.9, "label": "line-1", "speaker_id": "speaker-a"},
        {"start_sec": 3.1, "end_sec": 65.2, "label": "line-2", "speaker_id": "speaker-b"},
        {"start_sec": 65.5, "end_sec": 69.8, "label": "line-3", "speaker_id": "speaker-a"},
    ],
    "background_music": "focus-bed.mp3",
    "duration_seconds": 69.8,
    "loudness_lufs": -16.0,
    "error_message": None,
    "started_at": "2026-09-16T00:00:00Z",
    "completed_at": "2026-09-16T00:01:10Z",
}
TEMPLATES = [
    {
        "id": "midnight",
        "display_name": "Midnight",
        "preview_url": "/static/video_backgrounds/midnight.png",
    },
    {
        "id": "deep_purple",
        "display_name": "Deep Purple",
        "preview_url": "/static/video_backgrounds/deep_purple.png",
    },
]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
    port = _find_free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
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
        raise RuntimeError("Live test server failed to start within 10 seconds")
    yield f"http://127.0.0.1:{port}"


@pytest.fixture
async def browser_instance() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        yield browser
        await browser.close()


def _envelope(data, error=None) -> str:
    return json.dumps(
        {"success": error is None, "data": data, "error": error, "meta": {}}
    )


async def _mock_video_routes(
    page: Page,
    *,
    audio_status: int = 200,
    script_status: int = 200,
    event_log: list[tuple[str, str]] | None = None,
    audio_job_override: dict | None = None,
) -> None:
    project_state = json.loads(json.dumps(PROJECT))
    audio_job = audio_job_override if audio_job_override is not None else AUDIO_JOB

    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(project_state),
            )
        elif url.endswith("/audio/status") and method == "GET":
            if audio_status == 200:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=_envelope(audio_job),
                )
            else:
                await route.fulfill(
                    status=audio_status,
                    content_type="application/json",
                    body=_envelope(None, "No audio job"),
                )
        elif url.endswith("/script") and method == "GET":
            if event_log is not None:
                event_log.append(("script", "GET"))
            if script_status == 200:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=_envelope(LINES),
                )
            else:
                await route.fulfill(
                    status=script_status,
                    content_type="application/json",
                    body=_envelope(None, "Script unavailable"),
                )
        elif url.endswith("/api/video/templates") and method == "GET":
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(TEMPLATES),
            )
        elif url.endswith("/video/status") and method == "GET":
            await route.fulfill(
                status=404,
                content_type="application/json",
                body=_envelope(None, "No video job"),
            )
        elif url.endswith("/video/generate") and method == "POST":
            payload = json.loads(route.request.post_data or "{}")
            if event_log is not None:
                event_log.append(("generate", json.dumps(payload, sort_keys=True)))
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(
                    {
                        "project_id": PROJECT_ID,
                        "status": "complete",
                        "mp4_path": f"data/video/{PROJECT_ID}/video.mp4",
                        "mp4_path_vertical": (
                            f"data/video/{PROJECT_ID}/video_vertical.mp4"
                        ),
                        "srt_path": f"data/video/{PROJECT_ID}/subtitles.srt",
                    }
                ),
            )
        elif "/speakers/speaker-a/avatar" in url and method == "POST":
            project_state["speakers"][0]["avatar_image_path"] = (
                f"/api/projects/{PROJECT_ID}/speakers/speaker-a/avatar"
            )
            if event_log is not None:
                event_log.append(("avatar", "POST"))
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(project_state),
            )
        elif "/speakers/speaker-a/avatar" in url and method == "DELETE":
            project_state["speakers"][0]["avatar_image_path"] = None
            if event_log is not None:
                event_log.append(("avatar", "DELETE"))
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=_envelope(project_state),
            )
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_video_shell_resizes_and_keeps_music_single_across_selections(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_video_routes(page)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    assert await page.locator("#pane-sidebar .step-nav-workflow").count() == 1
    assert await page.locator("#pane-timeline .track-row").count() == 3
    assert await page.locator("#script-timeline [data-line-id]").count() == 3
    assert await page.locator("#voice-timeline [data-line-id]").count() == 3
    assert "Line 1" in await page.locator("#video-inspector").text_content()
    assert "Alex" in await page.locator("#video-inspector").text_content()
    assert "0:00 – 0:02" in await page.locator("#video-inspector").text_content()

    sidebar_before = await page.locator("#pane-sidebar").bounding_box()
    left_handle = await page.locator("#resizer-left").bounding_box()
    assert sidebar_before and left_handle
    await page.mouse.move(left_handle["x"] + 2, left_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(left_handle["x"] + 122, left_handle["y"] + 30)
    await page.mouse.up()
    sidebar_after = await page.locator("#pane-sidebar").bounding_box()
    assert sidebar_after and sidebar_after["width"] > sidebar_before["width"] + 80

    inspector_before = await page.locator("#pane-inspector").bounding_box()
    right_handle = await page.locator("#resizer-right").bounding_box()
    assert inspector_before and right_handle
    await page.mouse.move(right_handle["x"] + 2, right_handle["y"] + 30)
    await page.mouse.down()
    await page.mouse.move(right_handle["x"] - 82, right_handle["y"] + 30)
    await page.mouse.up()
    inspector_after = await page.locator("#pane-inspector").bounding_box()
    assert inspector_after
    assert inspector_after["width"] > inspector_before["width"] + 70

    timeline_before = await page.locator("#pane-timeline").bounding_box()
    top_handle = await page.locator("#resizer-top").bounding_box()
    assert timeline_before and top_handle
    await page.mouse.move(top_handle["x"] + 200, top_handle["y"] + 2)
    await page.mouse.down()
    await page.mouse.move(top_handle["x"] + 200, top_handle["y"] - 72)
    await page.mouse.up()
    timeline_after = await page.locator("#pane-timeline").bounding_box()
    assert timeline_after and timeline_after["height"] > timeline_before["height"] + 60

    await page.click("#sidebar-collapse-btn")
    assert await page.locator("#pane-sidebar").evaluate(
        "element => element.classList.contains('collapsed')"
    )

    for line_id, expected_line, expected_speaker, expected_timing in [
        ("line-2", "Line 2", "Sam", "0:03 – 1:05"),
        ("line-3", "Line 3", "Alex", "1:05 – 1:09"),
        ("line-1", "Line 1", "Alex", "0:00 – 0:02"),
    ]:
        await page.click(f"#script-timeline [data-line-id='{line_id}']")
        inspector_text = await page.locator("#video-inspector").text_content()
        assert expected_line in inspector_text
        assert expected_speaker in inspector_text
        assert expected_timing in inspector_text
        assert await page.locator("#music-timeline .timeline-clip").count() == 1
        assert "focus-bed.mp3" in await page.locator(
            "#music-timeline"
        ).text_content()

    await page.close()


@pytest.mark.asyncio
async def test_empty_audio_state_does_not_request_script(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    event_log: list[tuple[str, str]] = []
    await _mock_video_routes(page, audio_status=404, event_log=event_log)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT_ID}")
    await page.wait_for_selector("#empty-state:not([hidden])")

    assert ("script", "GET") not in event_log
    assert await page.locator("#workspace").is_hidden()
    assert await page.locator("#music-timeline .timeline-clip").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_video_timeline_widths_follow_measured_duration_and_fall_back_per_line(
    browser_instance: Browser, live_server_url: str
):
    partial_timing_job = {
        **AUDIO_JOB,
        "timestamps": [
            {"start_sec": 0.0, "end_sec": 3.0, "label": "line-1", "speaker_id": "speaker-a"},
            {"start_sec": 3.3, "end_sec": 10.3, "label": "line-2", "speaker_id": "speaker-b"},
        ],
    }
    page = await browser_instance.new_page()
    await _mock_video_routes(page, audio_job_override=partial_timing_job)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    for lane_id in ("script-timeline", "voice-timeline"):
        short_clip = page.locator(f"#{lane_id} [data-line-id='line-1']")
        long_clip = page.locator(f"#{lane_id} [data-line-id='line-2']")
        short_box = await short_clip.bounding_box()
        long_box = await long_clip.bounding_box()
        assert short_box and long_box
        assert long_box["width"] > short_box["width"] + 30
        assert await page.locator(
            f"#{lane_id} [data-line-id='line-3']"
        ).evaluate("clip => clip.style.width") == ""

    for line_id in ("line-1", "line-2"):
        script_box = await page.locator(
            f"#script-timeline [data-line-id='{line_id}']"
        ).bounding_box()
        voice_box = await page.locator(
            f"#voice-timeline [data-line-id='{line_id}']"
        ).bounding_box()
        assert script_box and voice_box
        assert abs(script_box["width"] - voice_box["width"]) < 1
    await page.close()


@pytest.mark.asyncio
async def test_script_failure_is_non_fatal_to_video_workflow(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_video_routes(page, script_status=404)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    assert await page.locator("#generate-btn").is_enabled()
    assert "Script unavailable" in await page.locator("#timeline-status").text_content()
    assert await page.locator("#music-timeline .timeline-clip").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_avatar_and_generate_flows_remain_wired(
    browser_instance: Browser, live_server_url: str, tmp_path
):
    page = await browser_instance.new_page()
    event_log: list[tuple[str, str]] = []
    await _mock_video_routes(page, event_log=event_log)
    await page.goto(f"{live_server_url}/step5?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    fixture = tmp_path / "avatar.png"
    fixture.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-bytes")
    await page.locator("#avatar-file-speaker-a").set_input_files(str(fixture))
    await page.wait_for_selector(".avatar-preview")
    await page.locator(".avatar-card:has-text('Alex') button:has-text('Remove')").click()
    await page.wait_for_function(
        "document.querySelectorAll('.avatar-placeholder').length === 2"
    )

    await page.click("[data-template-id='deep_purple']")
    await page.click("[data-aspect-ratio='9:16']")
    await page.click("#generate-btn")
    await page.wait_for_selector("#result-card:not([hidden])")

    assert ("avatar", "POST") in event_log
    assert ("avatar", "DELETE") in event_log
    expected_payload = json.dumps(
        {"template_id": "deep_purple", "aspect_ratio": "9:16"}, sort_keys=True
    )
    assert ("generate", expected_payload) in event_log
    assert await page.locator("#download-mp4-vertical").is_visible()
    await page.close()
