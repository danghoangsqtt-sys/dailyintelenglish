"""Browser coverage for Task 4.2b's TTS workspace shell, timeline, and inspector."""

import asyncio
import json
import socket
import threading
import time
from typing import AsyncGenerator

import pytest
import uvicorn
from playwright.async_api import Browser, Page, async_playwright

from app.main import app

PROJECT_ID = "tts-shell-project"
PROJECT = {
    "id": PROJECT_ID,
    "name": "TTS Shell Test",
    "status": "script_generated",
    "topic": "Testing the audio workspace",
    "cefr_level": "B1",
    "genre": "interview",
    "speakers": [
        {
            "id": "speaker-a",
            "name": "Alex",
            "gender": "male",
            "accent": "american",
            "tts_engine": "edge_tts",
            "speed": 1.0,
            "pitch": 0.0,
            "volume": 1.0,
        },
        {
            "id": "speaker-b",
            "name": "Sam",
            "gender": "female",
            "accent": "british",
            "tts_engine": "edge_tts",
            "speed": 1.0,
            "pitch": 0.0,
            "volume": 1.0,
        },
    ],
}
LINES = [
    {
        "id": "line-1",
        "line_index": 0,
        "speaker_id": "speaker-a",
        "text": "How has remote work changed your team?",
        "language_notes": None,
        "duration_seconds": None,
    },
    {
        "id": "line-2",
        "line_index": 1,
        "speaker_id": "speaker-b",
        "text": "It has made our planning more deliberate.",
        "language_notes": None,
        "duration_seconds": None,
    },
]
MUSIC_TRACKS = [
    {
        "filename": "focus-bed.mp3",
        "size_bytes": 4096,
        "content_url": "/api/music/focus-bed.mp3",
    }
]
AUDIO_JOB = {
    "project_id": PROJECT_ID,
    "status": "complete",
    "mp3_path": f"data/audio/{PROJECT_ID}/mix.mp3",
    "wav_path": f"data/audio/{PROJECT_ID}/mix.wav",
    "timestamps": [
        {"start_sec": 0.0, "end_sec": 3.0, "label": "line-1", "speaker_id": "speaker-a"},
        {"start_sec": 3.3, "end_sec": 10.3, "label": "line-2", "speaker_id": "speaker-b"},
    ],
    "background_music": "focus-bed.mp3",
    "duration_seconds": 10.3,
    "loudness_lufs": -16.0,
    "error_message": None,
    "started_at": "2026-09-15T00:00:00Z",
    "completed_at": "2026-09-15T00:00:01Z",
}


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
    return json.dumps({"success": error is None, "data": data, "error": error, "meta": {}})


async def _mock_tts_routes(
    page: Page,
    *,
    event_log: list[tuple[str, str]] | None = None,
    preview_status: int = 200,
    patch_probe: dict | None = None,
    audio_job: dict | None = None,
) -> None:
    async def handle(route):
        url, method = route.request.url, route.request.method
        if url.endswith(f"/api/projects/{PROJECT_ID}") and method == "GET":
            await route.fulfill(
                status=200, content_type="application/json", body=_envelope(PROJECT)
            )
        elif url.endswith(f"/api/projects/{PROJECT_ID}/script") and method == "GET":
            await route.fulfill(
                status=200, content_type="application/json", body=_envelope(LINES)
            )
        elif "/speakers/" in url and method == "PATCH":
            payload = json.loads(route.request.post_data or "{}")
            if patch_probe is not None:
                patch_probe["bodies"].append(payload)
                patch_probe["active"] += 1
                patch_probe["max_active"] = max(
                    patch_probe["max_active"], patch_probe["active"]
                )
                await asyncio.sleep(0.25)
                patch_probe["active"] -= 1
            await route.fulfill(
                status=200, content_type="application/json", body=_envelope(PROJECT)
            )
        elif url.endswith("/api/music") and method == "GET":
            await route.fulfill(
                status=200, content_type="application/json", body=_envelope(MUSIC_TRACKS)
            )
        elif url.endswith("/audio/status") and method == "GET":
            if audio_job is None:
                await route.fulfill(
                    status=404,
                    content_type="application/json",
                    body=_envelope(None, "No audio job"),
                )
            else:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=_envelope(audio_job),
                )
        elif url.endswith("/tts/preview") and method == "POST":
            payload = json.loads(route.request.post_data or "{}")
            if event_log is not None:
                event_log.append(("preview", payload["line_id"]))
            if preview_status == 200:
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=_envelope(
                        {"audio_path": "cached.mp3", "engine_used": "edge_tts"}
                    ),
                )
            else:
                await route.fulfill(
                    status=preview_status,
                    content_type="application/json",
                    body=_envelope(None, "Provider secret detail"),
                )
        elif "/tts/cache/" in url and method == "GET":
            await route.fulfill(status=200, content_type="audio/mpeg", body=b"")
        elif url.endswith("/audio/generate") and method == "POST":
            payload = json.loads(route.request.post_data or "{}")
            if event_log is not None:
                event_log.append(("generate", payload.get("background_music") or ""))
            await route.fulfill(
                status=200, content_type="application/json", body=_envelope(AUDIO_JOB)
            )
        else:
            await route.continue_()

    await page.route("**/api/**", handle)


@pytest.mark.asyncio
async def test_tts_shell_resizes_collapses_and_syncs_three_track_selection(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_tts_routes(page)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    assert await page.locator("#pane-sidebar #step-nav .step-nav-workflow").count() == 1
    assert await page.locator("#pane-timeline .track-row").count() == 3
    assert await page.locator("#script-timeline .timeline-clip").count() == 2
    assert await page.locator("#voice-timeline .timeline-clip").count() == 2
    assert "Line 1" in await page.locator("#tts-inspector").text_content()

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
    assert inspector_after and inspector_after["width"] > inspector_before["width"] + 70

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

    await page.click("#script-timeline [data-line-id='line-2']")
    assert "Line 2" in await page.locator("#tts-inspector").text_content()
    assert await page.locator("#line-list .line-card[data-line-id='line-2']").evaluate(
        "element => element.classList.contains('selected')"
    )
    assert await page.locator("#voice-timeline [data-line-id='line-2']").evaluate(
        "element => element.classList.contains('active')"
    )

    await page.click("[data-inspector-action='voice-settings']")
    await page.wait_for_function(
        "document.activeElement?.dataset.speakerId === 'speaker-b'"
    )
    await page.select_option("#music-select", "focus-bed.mp3")
    assert "focus-bed.mp3" in await page.locator("#music-timeline").text_content()
    assert await page.locator("#music-timeline .timeline-clip").count() == 1
    await page.close()


@pytest.mark.asyncio
async def test_inspector_listen_calls_preview_and_reload_resets_session_state(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    event_log: list[tuple[str, str]] = []
    await _mock_tts_routes(page, event_log=event_log)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("[data-inspector-action='listen']")

    await page.click("[data-inspector-action='listen']")
    await page.wait_for_function(
        "document.querySelector('#inspector-audio')?.src.includes('/tts/cache/line-1.mp3')"
    )
    await page.wait_for_selector(
        "#voice-timeline [data-line-id='line-1'][data-preview-state='preview-ready']"
    )

    assert event_log == [("preview", "line-1")]
    assert await page.locator("#inspector-audio").is_hidden() is False
    assert "Preview ready" in await page.locator("#tts-inspector").text_content()

    await page.reload()
    await page.wait_for_selector("#workspace:not([hidden])")
    assert (
        await page.locator("#voice-timeline [data-line-id='line-1']").get_attribute(
            "data-preview-state"
        )
        == "not-previewed"
    )
    await page.close()


@pytest.mark.asyncio
async def test_existing_audio_uses_measured_widths_and_missing_audio_keeps_auto_width(
    browser_instance: Browser, live_server_url: str
):
    timed_page = await browser_instance.new_page()
    await _mock_tts_routes(timed_page, audio_job=AUDIO_JOB)
    await timed_page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await timed_page.wait_for_selector("#workspace:not([hidden])")

    for lane_id in ("script-timeline", "voice-timeline"):
        short_clip = timed_page.locator(f"#{lane_id} [data-line-id='line-1']")
        long_clip = timed_page.locator(f"#{lane_id} [data-line-id='line-2']")
        short_box = await short_clip.bounding_box()
        long_box = await long_clip.bounding_box()
        assert short_box and long_box
        assert long_box["width"] > short_box["width"] + 30

    first_script_width = await timed_page.locator(
        "#script-timeline [data-line-id='line-1']"
    ).bounding_box()
    first_voice_width = await timed_page.locator(
        "#voice-timeline [data-line-id='line-1']"
    ).bounding_box()
    assert first_script_width and first_voice_width
    assert abs(first_script_width["width"] - first_voice_width["width"]) < 1
    await timed_page.close()

    untimed_page = await browser_instance.new_page()
    await _mock_tts_routes(untimed_page)
    await untimed_page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await untimed_page.wait_for_selector("#workspace:not([hidden])")
    for lane_id in ("script-timeline", "voice-timeline"):
        widths = await untimed_page.locator(f"#{lane_id} [data-line-id]").evaluate_all(
            "clips => clips.map(clip => clip.style.width)"
        )
        assert widths == ["", ""]
    await untimed_page.close()


@pytest.mark.asyncio
async def test_horizontal_timeline_resizer_supports_keyboard_steps(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page(viewport={"width": 1440, "height": 900})
    await _mock_tts_routes(page)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    timeline = page.locator("#pane-timeline")
    handle = page.locator("#resizer-top")
    await handle.focus()
    initial = await timeline.bounding_box()
    assert initial

    await page.keyboard.press("ArrowUp")
    after_up = await timeline.bounding_box()
    assert after_up and after_up["height"] > initial["height"] + 8

    await page.keyboard.press("ArrowDown")
    after_down = await timeline.bounding_box()
    assert after_down and abs(after_down["height"] - initial["height"]) < 2

    await page.keyboard.press("Shift+ArrowUp")
    after_shift_up = await timeline.bounding_box()
    assert after_shift_up and after_shift_up["height"] > after_down["height"] + 35

    await page.keyboard.press("Shift+ArrowDown")
    after_shift_down = await timeline.bounding_box()
    assert after_shift_down and abs(after_shift_down["height"] - initial["height"]) < 2
    await page.close()


@pytest.mark.asyncio
async def test_inspector_listen_failure_is_friendly_and_unlocks(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    await _mock_tts_routes(page, preview_status=502)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("[data-inspector-action='listen']")

    await page.click("[data-inspector-action='listen']")
    await page.wait_for_selector("#error-banner:not([hidden])")

    banner = await page.locator("#error-banner").text_content()
    assert "couldn't synthesize" in banner.lower()
    assert "Provider secret detail" not in banner
    assert await page.locator("[data-inspector-action='listen']").is_enabled()
    assert "Not previewed" in await page.locator("#tts-inspector").text_content()
    await page.close()


@pytest.mark.asyncio
async def test_speaker_autosave_remains_serialized_with_one_trailing_patch(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    patch_probe = {"bodies": [], "active": 0, "max_active": 0}
    await _mock_tts_routes(page, patch_probe=patch_probe)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    slider = page.locator(
        ".speaker-card[data-speaker-id='speaker-a'] input[data-field='speed']"
    )
    await slider.evaluate(
        "element => { element.value = '1.10'; "
        "element.dispatchEvent(new Event('input', { bubbles: true })); }"
    )
    await page.wait_for_timeout(450)
    await slider.evaluate(
        "element => { element.value = '1.25'; "
        "element.dispatchEvent(new Event('input', { bubbles: true })); }"
    )

    started_at = time.time()
    while len(patch_probe["bodies"]) < 2 and time.time() - started_at < 5.0:
        await page.wait_for_timeout(50)

    assert patch_probe["bodies"] == [{"speed": 1.1}, {"speed": 1.25}]
    assert patch_probe["max_active"] == 1
    await page.close()


@pytest.mark.asyncio
async def test_generate_all_keeps_preview_then_mix_order(
    browser_instance: Browser, live_server_url: str
):
    page = await browser_instance.new_page()
    event_log: list[tuple[str, str]] = []
    await _mock_tts_routes(page, event_log=event_log)
    await page.goto(f"{live_server_url}/step4?project_id={PROJECT_ID}")
    await page.wait_for_selector("#workspace:not([hidden])")

    await page.select_option("#music-select", "focus-bed.mp3")
    await page.click("#generate-btn")
    await page.wait_for_selector("#result-card:not([hidden])")

    assert event_log == [
        ("preview", "line-1"),
        ("preview", "line-2"),
        ("generate", "focus-bed.mp3"),
    ]
    assert await page.locator(
        "#voice-timeline [data-preview-state='preview-ready']"
    ).count() == 2
    short_box = await page.locator(
        "#voice-timeline [data-line-id='line-1']"
    ).bounding_box()
    long_box = await page.locator(
        "#voice-timeline [data-line-id='line-2']"
    ).bounding_box()
    assert short_box and long_box
    assert long_box["width"] > short_box["width"] + 30
    await page.close()
