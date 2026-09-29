"""Gate B-12: real ffmpeg + Remotion renders on 3 episodes for visual sign-off + media gate.

Runs a real, unmodified `app.main:app` instance on an isolated port + copy of
`data/app.db` in a temp directory. Never touches the running :8000 dev server or the
real DB. Same isolated-verification pattern Task 19.7 established.

3 real B1/A2 episodes with completed audio:
- b330d37f... (B1, 2:56) — Phase 19 baseline
- c08ce057... (B1, 5:00) — mid
- 22484f26... (A2, 9:26) — longest, different CEFR

Each episode is rendered twice: once via `renderer=ffmpeg` (baseline), once via
`renderer=remotion`. Wall time + real API response + ffprobe metadata captured.

Usage:
    venv\\Scripts\\python scripts\\run_gate_b12.py
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "operations" / "gate-b12-evidence"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EPISODES = [
    ("b330d37f-a212-4cf7-a779-7a109098bd6c", "B1 2:56 baseline"),
    ("c08ce057-792a-44db-be5d-2585e6600f4b", "B1 5:00 mid"),
    ("22484f26-f944-40db-8064-44088ccdb507", "A2 9:26 longest"),
]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _setup_isolated_env() -> tuple[Path, Path]:
    """Copy data/app.db + data/audio + data/video into a temp dir. Return (tmp_dir, tmp_data_dir)."""
    tmp = Path(tempfile.mkdtemp(prefix="gate_b12_"))
    tmp_data = tmp / "data"
    tmp_data.mkdir()

    print(f"[setup] tmp dir: {tmp}", flush=True)
    for name in ["app.db", "audio", "video", "avatars", "tts_cache", "music_library",
                 "thumbnails", "learning", "quality_reviews"]:
        src = REPO_ROOT / "data" / name
        if src.exists():
            dst = tmp_data / name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            print(f"[setup] copied data/{name}", flush=True)

    # video-renderer path stays shared (read-only from Coder's Node subprocess POV)
    return tmp, tmp_data


def _start_isolated_server(port: int, tmp_data_dir: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["DIE_DATA_DIR"] = str(tmp_data_dir)
    env["DIE_AI_MODE"] = "cloud_first"  # match real default
    # Task 19.7 D19.7-b: kill switch enforces ffmpeg unless env explicitly says "remotion".
    # Gate B-12 needs BOTH paths callable, so opt in via env here for the isolated instance.
    env["DIE_VIDEO_RENDERER"] = "remotion"
    env["PYTHONUNBUFFERED"] = "1"
    print(f"[server] starting uvicorn on :{port} with DIE_DATA_DIR={tmp_data_dir}", flush=True)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO_ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    # wait for readiness
    for _ in range(60):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("isolated server failed to start within 30s")
    print(f"[server] ready on :{port}", flush=True)
    return proc


def _ffprobe(path: Path) -> dict:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,duration",
         "-show_entries", "format=duration,size",
         "-of", "json", str(path)],
        text=True, encoding="utf-8",
    )
    return json.loads(out)


def _render(base_url: str, project_id: str, renderer: str, out_dir: Path) -> dict:
    print(f"  [{renderer}] POST /api/projects/{project_id[:8]}../video/generate ...", flush=True)
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{base_url}/api/projects/{project_id}/video/generate",
            json={"renderer": renderer, "template_id": "midnight"},
            timeout=900,
        )
    except Exception as e:
        return {"ok": False, "error": f"http exception: {e!r}", "wall_seconds": time.monotonic() - t0}
    dt = time.monotonic() - t0
    print(f"  [{renderer}] HTTP {r.status_code}, {dt:.1f}s", flush=True)

    result: dict = {"http_status": r.status_code, "wall_seconds": dt}
    try:
        result["body"] = r.json()
    except Exception:
        result["body_text"] = r.text[:500]
        result["ok"] = False
        return result

    if r.status_code != 200:
        result["ok"] = False
        return result

    # download the rendered video via /video/download
    dl = httpx.get(
        f"{base_url}/api/projects/{project_id}/video/download",
        timeout=60,
    )
    if dl.status_code != 200:
        result["ok"] = False
        result["download_error"] = f"HTTP {dl.status_code}: {dl.text[:200]}"
        return result

    out_path = out_dir / f"{project_id[:8]}_{renderer}.mp4"
    out_path.write_bytes(dl.content)
    result["output_path"] = str(out_path.relative_to(REPO_ROOT))
    result["output_bytes"] = out_path.stat().st_size

    try:
        result["ffprobe"] = _ffprobe(out_path)
    except Exception as e:
        result["ffprobe_error"] = repr(e)

    result["ok"] = True
    return result


def main() -> int:
    tmp_dir, tmp_data = _setup_isolated_env()
    port = _find_free_port()
    proc = _start_isolated_server(port, tmp_data)
    base_url = f"http://127.0.0.1:{port}"

    all_results: list[dict] = []
    try:
        # First: check /api/video/health exists (Task 19.7 D19.7-d)
        try:
            r = httpx.get(f"{base_url}/api/video/health", timeout=10)
            print(f"[health] /api/video/health → HTTP {r.status_code}, "
                  f"body: {r.text[:200]}", flush=True)
        except Exception as e:
            print(f"[health] /api/video/health → {e!r}", flush=True)

        for pid, label in EPISODES:
            print(f"\n=== Episode {pid[:8]}... ({label}) ===", flush=True)
            ffmpeg_result = _render(base_url, pid, "ffmpeg", OUTPUT_DIR)
            remotion_result = _render(base_url, pid, "remotion", OUTPUT_DIR)
            all_results.append({
                "project_id": pid,
                "label": label,
                "ffmpeg": ffmpeg_result,
                "remotion": remotion_result,
            })

        # Final health snapshot
        try:
            r = httpx.get(f"{base_url}/api/video/health", timeout=10)
            print(f"\n[health-final] /api/video/health → {r.text[:300]}", flush=True)
            all_results.append({"health_final": r.json() if r.status_code == 200 else r.text[:300]})
        except Exception as e:
            print(f"[health-final] error: {e!r}", flush=True)

    finally:
        print("\n[server] terminating isolated instance ...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        # keep tmp dir on failure for debug; delete on success
        print(f"[server] tmp dir left at: {tmp_dir} (delete manually if all good)", flush=True)

    evidence_path = OUTPUT_DIR / "gate-b12-runs.json"
    evidence_path.write_text(
        json.dumps(all_results, indent=2, default=str), encoding="utf-8"
    )
    print(f"\n[done] evidence: {evidence_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
