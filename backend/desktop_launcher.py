"""Desktop entrypoint for the packaged .exe build (Task 12.2).

The dev workflow (`uvicorn backend.main:app --reload`) doesn't work in a frozen
PyInstaller build -- `--reload` spawns a subprocess by re-invoking the running
script's own file path, which isn't meaningful once frozen. This calls
`uvicorn.run()` programmatically instead (no reload), and auto-opens the user's
browser once the port actually accepts connections, so double-clicking the exe
feels like launching an app, not starting a bare server.
"""

import socket
import json
import sys
import threading
import time
import webbrowser
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from backend.core.build_info import get_instance_info
from backend.core.desktop_runtime import configure_desktop_runtime


def _is_port_open(host: str, port: int) -> bool:
    """True if something is already listening on host:port (a second launch)."""
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _read_running_instance(url: str) -> dict | None:
    """Read only Studio's small local identity endpoint, bypassing proxy settings."""
    try:
        with build_opener(ProxyHandler({})).open(f"{url}/api/system/build", timeout=1) as response:
            payload = json.loads(response.read(65536))
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else None
    except (OSError, URLError, ValueError):
        return None


def _same_instance(actual: dict | None, expected: dict) -> bool:
    return actual is not None and all(actual.get(key) == expected[key] for key in ("product", "build_id", "instance_id"))


def _reuse_existing_instance(url: str, expected: dict) -> None:
    """Open only the intended build and database; leave other processes untouched."""
    if not _same_instance(_read_running_instance(url), expected):
        raise RuntimeError(
            f"Another Studio build or application is already using {url}.\n"
            "Finish any running jobs and close the previous Studio before opening this build.\n"
            "For a Desktop upgrade, use scripts/install_desktop.ps1 with the verified staging folder; "
            "it checks active jobs and backs up your data and previous application."
        )
    webbrowser.open(url)


def _open_browser_when_ready(url: str, expected: dict, timeout: float = 60.0) -> None:
    """Wait for this build's HTTP readiness, including migrations, before opening."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _same_instance(_read_running_instance(url), expected):
            webbrowser.open(url)
            return
        time.sleep(0.2)
    # Never open an unverified port: it may belong to another process. Leave a trace instead.
    if sys.stderr is not None:
        sys.stderr.write(f"Studio was not ready at {url} after {timeout:.0f} s; open it manually once startup finishes.\n")


def main() -> None:
    """Start the desktop server, or open its existing instance on a second click."""
    if getattr(sys, "frozen", False):
        import multiprocessing

        multiprocessing.freeze_support()

    configure_desktop_runtime()
    import uvicorn

    from backend.core.config import settings

    host = settings.APP_HOST
    port = settings.APP_PORT
    browser_host = "127.0.0.1" if host == "0.0.0.0" else ("[::1]" if host == "::" else host)
    url = f"http://{browser_host}:{port}"
    expected = get_instance_info(settings.DATA_DIR)

    if _is_port_open(host, port):
        _reuse_existing_instance(url, expected)
        return

    from backend.main import app

    threading.Thread(target=_open_browser_when_ready, args=(url, expected), daemon=True).start()
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback

        detail = traceback.format_exc()
        if sys.stderr is not None:
            sys.stderr.write(detail)
        if getattr(sys, "frozen", False) and sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, f"Daily Beyond English could not start.\n\n{exc}\n\nSee data/logs/desktop.log for details.",
                                            "Daily Beyond English", 0x10)
        raise SystemExit(1) from exc
