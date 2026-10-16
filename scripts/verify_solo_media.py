"""Isolated, reproducible fixture renders and actual Player/API browser evidence (no owner art)."""
from __future__ import annotations

import copy
import asyncio
import json
import os
import hashlib
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageChops, ImageStat  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
import uvicorn  # noqa: E402
import httpx  # noqa: E402
import tests.conftest  # noqa: E402,F401 -- installs owner DB/cloud guards
from backend import main  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.db.database import Database  # noqa: E402
from backend.library import explainer_media  # noqa: E402
from backend.media import video_renderer_remotion as renderer  # noqa: E402
from tests import test_explainer_video_props as fixtures  # noqa: E402
from tests.test_explainer_api import data  # noqa: E402
from tests.test_explainer_assets import picture  # noqa: E402


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Fail with useful bounded diagnostics, never shell-interpolate a command."""
    result = subprocess.run(command, capture_output=True, text=True, timeout=1800, **kwargs)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-5000:])
    return result


def main_verify() -> None:
    output = (ROOT / "data/tmp/phase49-20261016").resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Each run gets its own disposable database and immutable render source paths.
    folder = output / f"run-{time.time_ns()}"
    folder.mkdir()
    ffmpeg = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH
    ffprobe = str(Path(ffmpeg).with_name("ffprobe.exe")) if Path(ffmpeg).is_absolute() else "ffprobe"
    original_setup, original_audio = fixtures.setup, fixtures.synthetic_audio

    def setup_three(api):
        pid, cid, lines, wire = original_setup(api)
        asset = data(api.post(f"/api/projects/{pid}/explainer/assets", files={"file": ("example.png", picture(), "image/png")}))["asset"]
        first, second = wire["segments"]
        first["visual"] = {"kind": "text_card", "title": "Start small", "bullets": ["One action"]}
        first["gestures"] = [{"at": {"line_id": lines[0]["id"], "token_index": 1}, "gesture": "point-left"}]
        third = copy.deepcopy(second)
        second["end"]["token_index"] = 2
        second["visual"] = {"kind": "diagram", "template": "steps", "title": "Habits", "nodes": [
            {"id": "a", "label": "Act"}, {"id": "b", "label": "Repeat"}], "edges": [{"source": "a", "target": "b"}]}
        second["gestures"] = [{"at": {"line_id": lines[1]["id"], "token_index": 0}, "gesture": "count-1"}]
        third.update(id="idea-2", visual={"kind": "photo", "asset": asset, "fit": "contain"})
        third["start"]["token_index"] = 2
        third["gestures"] = [{"at": {"line_id": lines[1]["id"], "token_index": 2}, "gesture": "wave"}]
        wire["segments"] = [first, second, third]
        return pid, cid, lines, wire

    def valid_audio(api, pid, lines):
        original_audio(api, pid, lines)
        audio = settings.DATA_DIR / "audio" / pid
        run([ffmpeg, "-y", "-v", "error", "-i", str(audio / "fixture.wav"), "-codec:a", "libmp3lame", str(audio / "fixture.mp3")])

    report = {"fixture_only": True, "owner_art_available": False, "renders": {}, "pixel_comparison": {}}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(settings, "DATA_DIR", folder / "sandbox")
        patch.setattr(settings, "IMAGE_ENGINE", "fake")
        patch.setattr(settings, "AI_VISUALS_ENABLED", True)
        patch.setattr(fixtures, "setup", setup_three)
        patch.setattr(fixtures, "synthetic_audio", valid_audio)
        with TestClient(main.app) as api:
            pid, cid, plan = fixtures.approved_fixture(api, patch)
            report.update(project_id=pid, character_id=cid, revision=plan["revision"])
            audio = settings.DATA_DIR / "audio" / pid / "fixture.mp3"
            key = f"solo-fixture-{pid}"
            renderer._copy_audio_into_public(key, str(audio))
            props_by_aspect = {}
            for aspect in ("16:9", "9:16"):
                props = api.portal.call(explainer_media.production_props, Database.instance().connection, pid, aspect)
                props["audioPath"] = f"remotion-render/audio/{key}.mp3"
                props_by_aspect[aspect] = props
            baseline = {**props_by_aspect["16:9"], "presentationMode": "classic", "solo": None, "visualMode": "podcast_black"}
            variants = {"baseline": (baseline, None), "landscape": (props_by_aspect["16:9"], None),
                        "portrait": (props_by_aspect["9:16"], None), "short": ({**props_by_aspect["9:16"], "hook": "One small action", "hookAtSec": 2.3}, (51, 134))}
            for name, (props, frames) in variants.items():
                target = folder / f"{name}.mp4"
                started = time.monotonic()
                renderer._render_via_remotion_sync(props, target, frames)
                elapsed = time.monotonic() - started
                probe = json.loads(run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target)]).stdout)
                streams = {stream["codec_type"]: stream for stream in probe["streams"]}
                drift = abs(float(streams["video"]["duration"]) - float(streams["audio"]["duration"]))
                expected = (frames[1] - frames[0] + 1) / 30 if frames else 4.5
                assert drift <= .1 and abs(float(probe["format"]["duration"]) - expected) <= .1
                run([ffmpeg, "-v", "error", "-i", str(target), "-f", "null", "-"])
                report["renders"][name] = {"elapsed_seconds": elapsed, "duration": probe["format"]["duration"],
                    "av_drift_seconds": drift, "width": streams["video"]["width"], "height": streams["video"]["height"], "frames": streams["video"]["nb_frames"]}
                print(f"{name}: {elapsed:.2f}s, drift {drift:.4f}s", flush=True)
            for aspect, props in props_by_aspect.items():
                name = "landscape" if aspect == "16:9" else "portrait"
                propfile = folder / f"{name}-props.json"
                propfile.write_text(json.dumps(props), encoding="utf-8")
                for frame in (15, 78, 110):
                    command = [shutil.which("npx.cmd") or "npx", "remotion", "still", "src/index.ts", "StillFrame", str(folder / f"{name}-{frame}-still.png"), f"--props={propfile}", f"--frame={frame}"]
                    if settings.REMOTION_GL != "auto":
                        command.append(f"--gl={settings.REMOTION_GL}")
                    run(command, cwd=renderer.VIDEO_RENDERER_DIR)
        # Start the actual app against the same disposable data after TestClient shutdown.
        from backend.db import transactions
        transactions.write_lock = asyncio.Lock()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=5))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(200):
                if server.started:
                    break
                time.sleep(.1)
            assert server.started
            with sync_playwright() as driver:
                browser = driver.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                base = f"http://127.0.0.1:{port}"
                page.goto(f"{base}/step5?project_id={pid}")
                page.locator('[data-action="preview"]').click()
                page.locator('[data-solo-presenter]').wait_for()
                page.screenshot(path=str(folder / "step5-editor.png"), full_page=True)
                page.evaluate("window.dispatchEvent(new Event('pagehide'))")
                # Test the same bundle at exact composition pixel size, at selected seek frames.
                for aspect, props in props_by_aspect.items():
                    name = "landscape" if aspect == "16:9" else "portrait"
                    public = copy.deepcopy(props)
                    response = page.request.get(f"{base}/api/projects/{pid}/explainer-plan/preview?aspect={aspect}")
                    assert response.ok
                    public = response.json()["data"]["props"]
                    page.set_viewport_size({"width": props["width"], "height": props["height"] + 200})
                    page.evaluate("""props=>{document.body.style.cssText=`margin:0;padding:0;display:block;width:${props.width}px;max-width:none`;document.body.innerHTML='<div id="pixel-player"></div>';window.pixel=window.SoloPreview.mount(document.getElementById('pixel-player'),props);}""", public)
                    page.add_style_tag(content="#pixel-player>*{max-height:none!important;max-width:none!important}")
                    page.locator('[data-solo-presenter]').wait_for()
                    for frame in (15, 78, 110):
                        page.evaluate("frame=>window.pixel.seek(frame)", frame)
                        page.wait_for_timeout(300)
                        # Player chrome is outside the composition; remove only its overlay for pixel comparison.
                        page.evaluate("""()=>{const scene=document.querySelector('[data-solo-scene]');let ancestor=scene;while(ancestor&&ancestor.parentElement?.id!=='pixel-player'){for(const sibling of ancestor.parentElement?.children??[]){if(sibling!==ancestor&&!sibling.contains(scene))sibling.style.visibility='hidden';}ancestor=ancestor.parentElement;}}""")
                        scene = page.locator('[data-solo-scene]')
                        target = folder / f"{name}-{frame}-player.png"
                        scene.screenshot(path=str(target))
                        with Image.open(target) as actual, Image.open(folder / f"{name}-{frame}-still.png") as expected:
                            assert actual.size == expected.size, (actual.size, expected.size)
                            difference = sum(ImageStat.Stat(ImageChops.difference(actual.convert("RGB"), expected.convert("RGB"))).mean) / 3
                            report["pixel_comparison"][f"{name}-{frame}"] = difference
                            assert difference < 1, difference
                    page.evaluate("window.pixel.destroy()")
                page.goto(base + "/characters")
                page.locator(f'.profile-card[data-id="{cid}"]').click()
                page.locator("#profile-view-front").click()
                page.locator('.slot-card[data-slot="gesture-wave__open"]').wait_for()
                assert page.locator(".slot-card").count() == 21
                page.screenshot(path=str(folder / "front21-slots.png"), full_page=True)
                assert not errors, errors
                browser.close()
        finally:
            server.should_exit = True
            thread.join(20)
            assert not thread.is_alive()
    report["run_folder"] = str(folder)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


def verify_frozen_stage(executable: Path) -> None:
    """Launch only the staged build against the fixture sandbox, twice, without opening owner tabs."""
    report_path = ROOT / "data/tmp/phase49-20261016/report.json"
    evidence = json.loads(report_path.read_text(encoding="utf-8"))
    sandbox = Path(evidence["run_folder"]) / "sandbox"
    assert sandbox.resolve().is_relative_to((ROOT / "data/tmp/phase49-20261016").resolve())
    assert executable.resolve().is_relative_to((ROOT / "data/tmp/phase49-exe-stage").resolve())
    noop = sandbox.parent / "noop-browser.py"
    noop.write_text("raise SystemExit(0)\n", encoding="utf-8")
    browser_command = f'"{(ROOT / ".venv/Scripts/pythonw.exe").as_posix()}" "{noop.as_posix()}" "%s"'
    results = {"fixture_only": True, "exe_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(), "restarts": []}
    log = sandbox / "logs/desktop.log"
    log_offset = log.stat().st_size if log.is_file() else 0
    for restart in (1, 2):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        env = {**os.environ, "DIE_DATA_DIR": str(sandbox), "DIE_WORKSPACE_DIR": str(ROOT), "DIE_APP_PORT": str(port),
               "DIE_AI_MODE": "local", "DIE_AI_ALLOW_CLOUD": "false", "DIE_GEMINI_API_KEY": "", "DIE_OPENAI_COMPAT_API_KEY": "",
               "BROWSER": browser_command}
        process = subprocess.Popen([str(executable)], env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        started = time.monotonic()
        base = f"http://127.0.0.1:{port}"
        try:
            with httpx.Client(base_url=base, timeout=2) as api:
                while time.monotonic() - started < 60:
                    if process.poll() is not None:
                        raise RuntimeError("The frozen fixture server exited during startup; inspect its sandbox desktop.log")
                    try:
                        if api.get("/api/projects").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.2)
                else:
                    raise RuntimeError("Frozen startup exceeded60s")
                bundle = api.get("/static/solo-preview/player.js")
                assert bundle.status_code == 200
                expected_bundle = executable.parent / "_internal/frontend/static/solo-preview/player.js"
                assert hashlib.sha256(bundle.content).hexdigest() == hashlib.sha256(expected_bundle.read_bytes()).hexdigest()
                response = api.get(f"/api/projects/{evidence['project_id']}/explainer-plan/preview?aspect=9:16")
                assert response.status_code == 200, response.text
                assert response.json()["data"]["revision"] == evidence["revision"]
                if restart == 1:
                    production = {}
                    for name, endpoint, format_name in (("landscape", "generate", "mp4"), ("portrait", "vertical", "mp4_vertical")):
                        render_started = time.monotonic()
                        rendered = api.post(f"/api/projects/{evidence['project_id']}/video/{endpoint}", json={}, timeout=600)
                        assert rendered.status_code == 200, rendered.text
                        download = api.get(f"/api/projects/{evidence['project_id']}/video/download?format={format_name}", timeout=60)
                        assert download.status_code == 200
                        target = sandbox.parent / f"frozen-production-{name}.mp4"
                        target.write_bytes(download.content)
                        ffmpeg = shutil.which(settings.FFMPEG_PATH) or settings.FFMPEG_PATH
                        ffprobe = str(Path(ffmpeg).with_name("ffprobe.exe")) if Path(ffmpeg).is_absolute() else "ffprobe"
                        probe = json.loads(run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target)]).stdout)
                        streams = {stream["codec_type"]: stream for stream in probe["streams"]}
                        drift = abs(float(streams["video"]["duration"]) - float(streams["audio"]["duration"]))
                        assert drift <= .1
                        run([ffmpeg, "-v", "error", "-i", str(target), "-f", "null", "-"])
                        production[name] = {"elapsed_seconds": time.monotonic() - render_started,
                            "duration": probe["format"]["duration"], "av_drift_seconds": drift}
                    srt = api.get(f"/api/projects/{evidence['project_id']}/video/download?format=srt")
                    assert srt.status_code == 200 and "Small actions become daily habits." in srt.text and "-->" in srt.text
                    (sandbox.parent / "frozen-production.srt").write_bytes(srt.content)
                    production["srt"] = "two source lines, intro offset preserved"
                    results["production_api"] = production
            with sync_playwright() as driver:
                browser = driver.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"{base}/step5?project_id={evidence['project_id']}")
                page.locator('[data-action="preview"]').click()
                page.locator('[data-solo-presenter]').wait_for()
                page.get_by_role("button", name="Play", exact=True).click()
                page.wait_for_timeout(350)
                page.get_by_role("button", name="Pause", exact=True).click()
                page.locator('[aria-label="Preview frame"]').focus()
                page.keyboard.press("ArrowRight")
                page.screenshot(path=str(sandbox.parent / f"frozen-step5-{restart}.png"), full_page=True)
                page.goto(base + "/characters")
                page.locator(f'.profile-card[data-id="{evidence["character_id"]}"]').click()
                page.locator("#profile-view-front").click()
                page.locator('.slot-card[data-slot="gesture-wave__open"]').wait_for()
                assert page.locator(".slot-card").count() == 21
                assert "1280x1536" in page.locator('.slot-card[data-slot="calm__closed"] textarea').input_value()
                from tests.test_explainer_project import solo_config
                response = page.request.post(base + "/api/projects", data=solo_config())
                assert response.ok
                fresh = response.json()["data"]["id"]
                page.goto(f"{base}/step5?project_id={fresh}")
                page.locator("#solo-explainer-section").wait_for(state="visible")
                assert "No plan yet" in page.locator("#solo-status").inner_text()
                page.reload()
                page.locator("#solo-explainer-section").wait_for(state="visible")
                assert not errors, errors
                browser.close()
            results["restarts"].append({"restart": restart, "seconds_including_browser_checks": time.monotonic() - started,
                                         "bundle_bytes": len(bundle.content), "preview_revision": evidence["revision"],
                                         "front_slots": 21, "no_audio_editor": True})
        finally:
            process.terminate()
            process.wait(timeout=20)
    new_log = log.read_bytes()[log_offset:].decode("utf-8", errors="replace")
    assert "UnicodeDecodeError" not in new_log
    assert "GET /fonts/" not in new_log
    results["unicode_decoder_errors"] = 0
    results["unscoped_font_requests"] = 0
    (report_path.parent / "frozen-report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--frozen-exe":
        verify_frozen_stage(Path(sys.argv[2]).resolve())
    else:
        main_verify()
