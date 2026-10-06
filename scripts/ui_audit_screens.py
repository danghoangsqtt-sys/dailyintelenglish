"""Phase 26 helper: screenshot every page (light + dark, desktop + narrow) against a running app.

    venv\\Scripts\\python scripts\\ui_audit_screens.py --out docs\\operations\\ui-audit\\before

Starts the app on a free port with the current DATA_DIR (read-only browsing: GET pages only).
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROJECT = "b330d37f-a212-4cf7-a779-7a109098bd6c"
PAGES = {
    "dashboard": "/", "step1": f"/step1?project_id={PROJECT}", "step2": f"/step2?project_id={PROJECT}",
    "step3": f"/step3?project_id={PROJECT}", "step4": f"/step4?project_id={PROJECT}",
    "step5": f"/step5?project_id={PROJECT}", "step6": f"/step6?project_id={PROJECT}",
    "step7": f"/step7?project_id={PROJECT}", "music": "/music", "characters": "/characters", "settings": "/settings",
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def shoot(base: str, out: Path, only: list[str] | None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for theme in ("light", "dark"):
            for width, tag in ((1440, "desktop"), (420, "narrow")):
                context = await browser.new_context(viewport={"width": width, "height": 900})
                await context.add_init_script(f"localStorage.setItem('die-theme', '{theme}')")
                page = await context.new_page()
                for name, path in PAGES.items():
                    if only and name not in only:
                        continue
                    await page.goto(base + path)
                    await page.wait_for_timeout(1800)
                    await page.screenshot(path=str(out / f"{name}-{theme}-{tag}.png"), full_page=tag == "desktop")
                await context.close()
        await browser.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "docs" / "operations" / "ui-audit" / "before"))
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    from app.main import app

    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning",
                                           timeout_graceful_shutdown=5))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
            break
        except OSError:
            time.sleep(0.1)
    try:
        asyncio.run(shoot(f"http://127.0.0.1:{port}", Path(args.out), args.only))
    finally:
        server.should_exit = True
        thread.join(timeout=20)
    print("done", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
