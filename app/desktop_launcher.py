"""Desktop entrypoint for the packaged .exe build (Task 12.2).

The dev workflow (`uvicorn app.main:app --reload`) doesn't work in a frozen
PyInstaller build -- `--reload` spawns a subprocess by re-invoking the running
script's own file path, which isn't meaningful once frozen. This calls
`uvicorn.run()` programmatically instead (no reload), and auto-opens the user's
browser once the port actually accepts connections, so double-clicking the exe
feels like launching an app, not starting a bare server.
"""

import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from app.core.config import settings
from app.main import app


def _is_port_open(host: str, port: int) -> bool:
    """True if something is already listening on host:port (a second launch)."""
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _open_browser_when_ready(url: str, host: str, port: int, timeout: float = 20.0) -> None:
    """Poll the server's own port with a plain TCP connect, then open the browser.

    A fixed sleep-then-open risks a "connection refused" flash on a slow cold
    start (SQLite migrations + the ffmpeg/GPU subprocess checks in app.main's
    lifespan); polling the real socket instead means the browser only opens once
    the server can actually answer.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _is_port_open(host, port):
            webbrowser.open(url)
            return
        time.sleep(0.2)


def main() -> None:
    if getattr(sys, "frozen", False):
        import multiprocessing

        multiprocessing.freeze_support()

    host = settings.APP_HOST
    port = settings.APP_PORT
    url = f"http://{host}:{port}"

    if _is_port_open(host, port):
        # Already running (e.g. the exe was double-clicked a second time) --
        # just open the browser to the existing instance instead of crashing on
        # a bind error.
        webbrowser.open(url)
        return

    threading.Thread(target=_open_browser_when_ready, args=(url, host, port), daemon=True).start()
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
