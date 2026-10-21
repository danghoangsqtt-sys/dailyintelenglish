"""Rehearse a frozen upgrade on copied owner profiles, or inspect the installed UI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.desktop_upgrade import backup_database  # noqa: E402

TABLES = ("projects", "characters", "character_assets", "speakers", "script_lines", "ai_generation_jobs", "ai_generation_checkpoints")


def snapshot(database: Path, columns: dict | None = None) -> dict:
    """Hash existing columns/rows without writing private profile or project content."""
    result = {}
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        for table in TABLES:
            fields = columns[table]["columns"] if columns else [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
            selection = ",".join(f'"{field}"' for field in fields)
            rows = sorted(json.dumps(row, ensure_ascii=True, default=str) for row in db.execute(f'SELECT {selection} FROM "{table}"'))
            result[table] = {"columns": fields, "count": len(rows), "sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest()}
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    return result


def asset_hashes(data: Path) -> dict:
    """Verify that native profile/sprite pictures survive migration and UI inspection."""
    return {str(path.relative_to(data)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ("library/characters", "library/sprites") for path in (data / folder).rglob("*") if path.is_file()}


def get_json(url: str) -> dict:
    """Read the local app envelope with a bounded deadline."""
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=5) as response:
        return json.load(response)["data"]


def browser_check(base: str, output: Path, *, destructive_fixture: bool) -> dict:
    """Inspect every existing profile; mutate only the disposable copy for error checks."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1500, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/characters")
        page.wait_for_selector(".profile-card")
        names = page.locator(".profile-card").all_text_contents()
        checked = []
        for index in range(len(names)):
            page.locator(".profile-card").nth(index).click()
            page.wait_for_function("document.querySelectorAll('.slot-card').length === 29")
            page.locator("#profile-tab-voice").click()  # Phase 58: the voice has its own profile tab
            assert page.locator("#profile-voice-picker .voice-select").is_visible()
            page.wait_for_function("document.querySelectorAll('#profile-voice-picker .voice-select option').length > 1", timeout=60000)
            page.locator("#profile-view-front").click()
            page.wait_for_function("document.querySelectorAll('.slot-card').length === 21")
            prompts = page.locator(".slot-prompt").evaluate_all("els => els.map(e => e.value)")
            assert all("1280" in prompt and "1536" in prompt for prompt in prompts)
            assert page.locator(".slot-card input[type=file]").count() == 21
            checked.append({"index": index, "native_slots": 29, "front_slots": 21, "strict_prompts": len(prompts), "voice_picker": True,
                            "voice_choices": page.locator("#profile-voice-picker .voice-select option").count() - 1})
            if "Hoang" in names[index]:
                page.screenshot(path=str(output / "hoang-front21.png"), full_page=True)
            if destructive_fixture and index == 0:
                page.locator(".slot-card input[type=file]:not([disabled])").first.set_input_files(
                    {"name": "invalid.png", "mimeType": "image/png", "buffer": b"invalid image"})
                page.wait_for_selector("#profile-message.is-error")
                assert "not a readable" in page.locator("#profile-message").inner_text()
            page.locator("#profile-view-native").click()
            page.wait_for_function("document.querySelectorAll('.slot-card').length === 29")
        page.reload()
        page.locator(".profile-card").filter(has_text="Hoang").click()
        page.wait_for_selector("#profile-voice-picker .voice-select", state="attached")
        page.locator("#profile-view-front").click()
        page.wait_for_function("document.querySelectorAll('.slot-card').length === 21")
        page.goto(base + "/settings")
        page.wait_for_function("document.querySelector('#running-build').textContent.includes('Build ')")
        label = page.locator("#running-build").inner_text()
        page.screenshot(path=str(output / "settings-build.png"), full_page=True)
        if destructive_fixture:
            page.route("**/api/system/build", lambda route: route.abort())
            page.reload()
            page.wait_for_function("document.querySelector('#running-build').textContent.includes('unavailable')")
            page.unroute("**/api/system/build")
            page.reload()
            page.wait_for_function("document.querySelector('#running-build').textContent.includes('Build ')")
        assert not errors, errors
        browser.close()
    return {"profiles": checked, "settings_build": label, "reload": True, "page_errors": errors}


def main() -> None:
    """Run bounded frozen trials without calling AI services or editing owner profiles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    output = ROOT / "data/tmp/phase51-upgrade"
    output.mkdir(parents=True, exist_ok=True)
    owner = ROOT / "data"
    if args.installed:
        for _ in range(120):
            try:
                get_json("http://127.0.0.1:8000/api/system/build")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.5)
        else:
            raise TimeoutError("Installed Studio did not become ready")
        before = snapshot(owner / "app.db")
        assets = asset_hashes(owner)
        result = browser_check("http://127.0.0.1:8000", output, destructive_fixture=False)
        assert snapshot(owner / "app.db", before) == before
        assert asset_hashes(owner) == assets
        result["identity"] = get_json("http://127.0.0.1:8000/api/system/build")
        (output / "installed-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
        return
    if not args.stage:
        parser.error("--stage or --installed is required")
    exe = args.stage.resolve(strict=True)
    if not exe.is_relative_to(ROOT / "data/tmp"):
        raise ValueError("Rehearsal executable must be under workspace data/tmp")
    copied = output / f"copy-{time.time_ns()}"
    copied.mkdir()
    counts = backup_database(owner / "app.db", copied / "app.db")
    before = snapshot(copied / "app.db")
    for name in ("library/characters", "library/sprites"):
        if (owner / name).is_dir():
            shutil.copytree(owner / name, copied / name)
    assets = asset_hashes(copied)
    noop = output / "noop_browser.py"
    noop.write_text("pass\n", encoding="utf-8")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = dict(os.environ, DIE_DATA_DIR=str(copied), DIE_WORKSPACE_DIR=str(ROOT), DIE_APP_PORT=str(port),
               DIE_AI_ALLOW_CLOUD="false", DIE_AI_MODE="local", DIE_OPENAI_COMPAT_API_KEY="", DIE_GEMINI_API_KEY="",
               DIE_OPENCODE_ZEN_API_KEY="", BROWSER=f'"{ROOT / ".venv/Scripts/pythonw.exe"}" "{noop}" %s')
    launches = []
    for launch in range(2):
        process = subprocess.Popen([str(exe)], cwd=ROOT, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError(f"Frozen rehearsal exited {process.returncode}")
                try:
                    identity = get_json(base + "/api/system/build")
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.5)
            else:
                raise TimeoutError("Frozen rehearsal did not become ready")
            assert identity["packaged"]
            if launch == 0:
                result = browser_check(base, output, destructive_fixture=True)
            assert snapshot(copied / "app.db", before) == before
            assert asset_hashes(copied) == assets
            launches.append(identity)
        finally:
            process.terminate()
            process.wait(timeout=30)
    assert launches[0] == launches[1]
    result.update(counts=counts, restarts=2, identity=launches[0], original_rows_preserved=True,
                  native_files_preserved=len(assets), data_copy=str(copied.relative_to(ROOT)))
    (output / "rehearsal-report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
