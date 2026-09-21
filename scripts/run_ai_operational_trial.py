"""Real no-mock operational trial and Gate B decision runner (Phase 13, Task 13.9).

Drives a real in-process `uvicorn` server (same pattern as `record_demo_video.py` and
the browser test suite's `live_server_url` fixture) over real HTTP via `httpx` --
never `fastapi.testclient.TestClient`, never a mocked provider. `DIE_AI_MODE=local` is
set before any `app.*` import so the trial genuinely has no Gemini fallback path, per
Gate B's own "fallback OFF" requirement. Local inference is real Ollama/qwen3.5:9b
(already qualified in Task 13.1's Gate A); learning generation and the final
audio/video pipeline are likewise driven only through the real running app.

Evidence lands under `data/quality_reviews/phase13/gate-b/` (gitignored via the
existing `data/quality_reviews/` entry -- the controlling plan's literal
`artifacts/phase13/gate-b/` path is not gitignored and `.gitignore` is not in this
task's allowed files, matching the same deviation Task 13.1 already made for Gate A).

Usage:
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py            # full Gate B
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --smoke-test  # fast sanity check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TRIAL_DATA_DIR = PROJECT_ROOT / "data" / "quality_reviews" / "phase13" / "gate-b" / "trial-data"
EVIDENCE_DIR = PROJECT_ROOT / "data" / "quality_reviews" / "phase13" / "gate-b"

# Must be set before any `app.*` import -- Settings() is a module-level singleton
# read from the environment once, at import time. argparse runs too late for that,
# so the mode is read straight off sys.argv here.
#
# `local` is Gate B's own requirement (fallback OFF) and stays the default. `--mode
# gemini` exists only for the provider-comparison diagnostic that the 2026-09-21 Gate B
# post-mortem asked for: the ±15%-per-section validator applies to *every* provider, so
# "does the primary provider clear the same bar?" had to be measurable, not assumed.
_MODE = "local"
if "--mode" in sys.argv:
    _MODE = sys.argv[sys.argv.index("--mode") + 1]
os.environ["DIE_AI_MODE"] = _MODE
os.environ["DIE_DATA_DIR"] = str(TRIAL_DATA_DIR)

import httpx  # noqa: E402
import uvicorn  # noqa: E402

from app.main import app  # noqa: E402

# --- Gate B thresholds (controlling plan section 8, Task 13.9 / section 3) ----------
WORD_COUNT_MIN, WORD_COUNT_MAX = 720, 880
SPEAKER_SHARE_MIN, SPEAKER_SHARE_MAX = 0.35, 0.65
REPEATED_8GRAM_MAX_RATIO = 0.01
FIRST_PROGRESS_MAX_SECONDS = 90.0
SCRIPT_JOB_MAX_MINUTES = 20.0
MEDIA_DURATION_MIN_SECONDS, MEDIA_DURATION_MAX_SECONDS = 432.0, 528.0
AV_DIFF_MAX_SECONDS = 1.0
B1_EIGHT_MIN_PASS_THRESHOLD = 4  # out of 5

SCRIPT_JOB_POLL_TIMEOUT_SECONDS = 25 * 60.0  # generous ceiling above the 20-minute cap
POLL_INTERVAL_SECONDS = 3.0

TOPIC = "How small daily habits shape long-term health"
GENRE = "interview"
ACCENT = "american"
SPEAKER_BLUEPRINTS = ({"name": "Alex", "gender": "male"}, {"name": "Maya", "gender": "female"})
LANGUAGE_FEATURES = {
    "collocation": True,
    "idiom": True,
    "slang": False,
    "local_expressions": False,
    "phrasal_verbs": True,
    "business_register": False,
}
VIDEO_TEMPLATE_ID = "midnight"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _start_live_server() -> tuple[uvicorn.Server, str, int]:
    """Start a real uvicorn server in-process on a fresh port -- never the dev
    server's own port 8000, which this script must never touch."""
    port = _find_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    started_at = time.time()
    while time.time() - started_at < 15.0:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    else:
        raise RuntimeError("Trial server failed to start within 15 seconds")
    return server, f"http://127.0.0.1:{port}", port


def _stop_live_server(server: uvicorn.Server) -> None:
    """Signal uvicorn's own run loop to exit; it has no public join(), so a short
    bounded wait is enough since this script's own process exits right after."""
    server.should_exit = True
    time.sleep(2.0)


def _speaker_payload(name: str, gender: str) -> dict[str, Any]:
    return {
        "name": name,
        "gender": gender,
        "accent": ACCENT,
        "tts_engine": "edge_tts",
        "voice_description": "",
        "speed": 1.0,
        "pitch": 0.0,
        "volume": 1.0,
    }


def _project_payload(cefr_level: str, duration_minutes: float, label: str) -> dict[str, Any]:
    return {
        "name": f"Gate B {label} {uuid.uuid4().hex[:8]}",
        "topic": TOPIC,
        "cefr_level": cefr_level,
        "duration_minutes": duration_minutes,
        "num_speakers": len(SPEAKER_BLUEPRINTS),
        "genre": GENRE,
        "accent": ACCENT,
        "language_features": LANGUAGE_FEATURES,
        "speakers": [_speaker_payload(b["name"], b["gender"]) for b in SPEAKER_BLUEPRINTS],
    }


async def create_project(client: httpx.AsyncClient, cefr_level: str, duration_minutes: float, label: str) -> dict:
    response = await client.post("/api/projects", json=_project_payload(cefr_level, duration_minutes, label))
    response.raise_for_status()
    return response.json()["data"]


async def create_and_wait_job(
    client: httpx.AsyncClient, project_id: str, operation: str
) -> dict[str, Any]:
    """POST an ai-job, poll until terminal, and return a timing/outcome record.

    `AIJobOut` deliberately excludes internal checkpoint-level bookkeeping (see
    app/models/ai_job.py), so per-section timing here is derived from observed
    `stage` transitions in the poll timeline, not read directly from the DB --
    an honest approximation given the API-only constraint this runner is under,
    not a claim of exact internal measurement.
    """
    request_started = time.monotonic()
    response = await client.post(f"/api/projects/{project_id}/ai-jobs", json={"operation": operation})
    response.raise_for_status()
    job = response.json()["data"]
    job_id = job["id"]

    timeline: list[dict[str, Any]] = []
    first_progress_at: float | None = None
    terminal_statuses = {"complete", "error", "cancelled", "stale"}

    while True:
        elapsed = time.monotonic() - request_started
        if elapsed > SCRIPT_JOB_POLL_TIMEOUT_SECONDS:
            job["timed_out"] = True
            break
        status_response = await client.get(f"/api/projects/{project_id}/ai-jobs/{job_id}")
        status_response.raise_for_status()
        job = status_response.json()["data"]
        timeline.append({"t": round(elapsed, 2), "status": job["status"], "stage": job["stage"], "progress": job["progress"]})
        if first_progress_at is None and (job["progress"] > 0 or job["stage"] not in ("pending", "")):
            first_progress_at = elapsed
        if job["status"] in terminal_statuses:
            break
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

    total_seconds = time.monotonic() - request_started
    stage_change_times = [0.0] + [entry["t"] for i, entry in enumerate(timeline) if i == 0 or entry["stage"] != timeline[i - 1]["stage"]]
    stage_change_times.append(total_seconds)
    longest_stage_gap = max(
        (b - a for a, b in zip(stage_change_times, stage_change_times[1:])), default=total_seconds
    )

    return {
        "job": job,
        "job_id": job_id,
        "total_seconds": round(total_seconds, 2),
        "first_progress_seconds": round(first_progress_at, 2) if first_progress_at is not None else None,
        "longest_stage_gap_seconds": round(longest_stage_gap, 2),
        "timeline": timeline,
    }


_WORD_RE = re.compile(r"[A-Za-z']+")


def _normalize_words(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def analyze_script(lines: list[dict], known_speaker_ids: set[str]) -> dict[str, Any]:
    """Independent, runner-side content check -- deliberately does not reuse
    script_pipeline.py's own validators, since Gate B measures the outcome, not
    re-trusts the code under test."""
    total_words = 0
    words_by_speaker: Counter[str] = Counter()
    texts = [line["text"] for line in lines]
    unknown_speakers = set()

    for line in lines:
        words = _normalize_words(line["text"])
        total_words += len(words)
        words_by_speaker[line["speaker_id"]] += len(words)
        if line["speaker_id"] not in known_speaker_ids:
            unknown_speakers.add(line["speaker_id"])

    speaker_shares = {
        speaker_id: (count / total_words if total_words else 0.0)
        for speaker_id, count in words_by_speaker.items()
    }
    balance_ok = bool(speaker_shares) and all(
        SPEAKER_SHARE_MIN <= share <= SPEAKER_SHARE_MAX for share in speaker_shares.values()
    )

    exact_duplicates = len(texts) - len({t.strip().lower() for t in texts})

    all_words = _normalize_words(" ".join(texts))
    eight_grams = [tuple(all_words[i : i + 8]) for i in range(len(all_words) - 7)] if len(all_words) >= 8 else []
    gram_counts = Counter(eight_grams)
    repeated_grams = sum(count - 1 for count in gram_counts.values() if count > 1)
    repeated_ratio = (repeated_grams / len(eight_grams)) if eight_grams else 0.0

    first_text = texts[0].lower() if texts else ""
    last_text = texts[-1].lower() if texts else ""
    intro_markers = ("welcome", "hello", "hi ", "today we", "let's talk", "glad to", "thanks for joining")
    outro_markers = ("thanks for", "thank you for", "see you", "that's all", "goodbye", "bye", "until next")
    has_intro = any(marker in first_text for marker in intro_markers)
    has_outro = any(marker in last_text for marker in outro_markers)

    checks = {
        "word_count_in_range": WORD_COUNT_MIN <= total_words <= WORD_COUNT_MAX,
        "speaker_balance_ok": balance_ok,
        "no_exact_duplicate_lines": exact_duplicates == 0,
        "repeated_8gram_ratio_ok": repeated_ratio < REPEATED_8GRAM_MAX_RATIO,
        "intro_present": has_intro,
        "outro_present": has_outro,
        "no_unknown_speaker_ids": not unknown_speakers,
    }
    return {
        "total_words": total_words,
        "speaker_shares": speaker_shares,
        "exact_duplicates": exact_duplicates,
        "repeated_8gram_ratio": round(repeated_ratio, 4),
        "has_intro": has_intro,
        "has_outro": has_outro,
        "unknown_speaker_ids": sorted(unknown_speakers),
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


async def run_script_trial(client: httpx.AsyncClient, cefr_level: str, duration_minutes: float, label: str) -> dict:
    project = await create_project(client, cefr_level, duration_minutes, label)
    known_speaker_ids = {s["id"] for s in project["speakers"]}
    result = await create_and_wait_job(client, project["id"], "script")
    job = result["job"]

    record: dict[str, Any] = {
        "label": label,
        "cefr_level": cefr_level,
        "duration_minutes": duration_minutes,
        "project_id": project["id"],
        "job_id": result["job_id"],
        "job_status": job["status"],
        "error_code": job.get("error_code"),
        "error_message": job.get("error_message"),
        "actual_provider": job.get("actual_provider"),
        "model": job.get("model"),
        "fallback_used": job.get("fallback_used"),
        "repair_count": job.get("repair_count"),
        "recovery_count": job.get("recovery_count"),
        "total_seconds": result["total_seconds"],
        "first_progress_seconds": result["first_progress_seconds"],
        "longest_stage_gap_seconds": result["longest_stage_gap_seconds"],
        "within_first_progress_threshold": (
            result["first_progress_seconds"] is not None
            and result["first_progress_seconds"] <= FIRST_PROGRESS_MAX_SECONDS
        ),
        "within_total_time_threshold": result["total_seconds"] <= SCRIPT_JOB_MAX_MINUTES * 60,
    }

    if job["status"] == "complete":
        script_response = await client.get(f"/api/projects/{project['id']}/script")
        script_response.raise_for_status()
        lines = script_response.json()["data"]
        record["line_count"] = len(lines)
        record["content"] = analyze_script(lines, known_speaker_ids)
    else:
        record["content"] = None

    return record


async def run_learning_trial(client: httpx.AsyncClient, project_id: str) -> dict:
    result = await create_and_wait_job(client, project_id, "learning")
    job = result["job"]
    record: dict[str, Any] = {
        "project_id": project_id,
        "job_id": result["job_id"],
        "job_status": job["status"],
        "error_code": job.get("error_code"),
        "error_message": job.get("error_message"),
        "total_seconds": result["total_seconds"],
    }
    if job["status"] == "complete":
        pack_response = await client.get(f"/api/projects/{project_id}/learning")
        pack_response.raise_for_status()
        pack = pack_response.json()["data"]
        vocab_words = [item["word"].strip().lower() for item in pack.get("vocabulary", [])]
        record["spot_check"] = {
            "has_vocabulary": len(pack.get("vocabulary", [])) > 0,
            "has_idioms": len(pack.get("idioms", [])) > 0,
            "has_grammar": len(pack.get("grammar", [])) > 0,
            "has_questions": len(pack.get("questions", [])) > 0,
            "no_duplicate_vocabulary": len(vocab_words) == len(set(vocab_words)),
        }
        record["spot_check_pass"] = all(record["spot_check"].values())
    return record


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe_info(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path),
        ],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        return {"ok": False, "stderr": proc.stderr[:500]}
    data = json.loads(proc.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "ok": True,
        "duration_seconds": float(fmt.get("duration", 0.0)),
        "size_bytes": int(fmt.get("size", 0)),
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
    }


async def run_media_pipeline(client: httpx.AsyncClient, project_id: str, evidence_dir: Path) -> dict:
    record: dict[str, Any] = {"project_id": project_id}

    audio_response = await client.post(f"/api/projects/{project_id}/audio/generate", json={})
    record["audio_generate_status_code"] = audio_response.status_code
    audio_response.raise_for_status()
    audio_job = audio_response.json()["data"]
    record["audio_job"] = {k: audio_job.get(k) for k in ("status", "duration_seconds", "loudness_lufs")}

    video_response = await client.post(
        f"/api/projects/{project_id}/video/generate",
        json={"template_id": VIDEO_TEMPLATE_ID, "aspect_ratio": "16:9"},
    )
    record["video_generate_status_code"] = video_response.status_code
    video_response.raise_for_status()
    video_job = video_response.json()["data"]
    record["video_job"] = {"status": video_job.get("status")}

    audio_bytes_response = await client.get(f"/api/projects/{project_id}/audio/download", params={"format": "mp3"})
    audio_bytes_response.raise_for_status()
    audio_path = evidence_dir / f"{project_id}-audio.mp3"
    audio_path.write_bytes(audio_bytes_response.content)

    video_bytes_response = await client.get(f"/api/projects/{project_id}/video/download", params={"format": "mp4"})
    video_bytes_response.raise_for_status()
    video_path = evidence_dir / f"{project_id}-video.mp4"
    video_path.write_bytes(video_bytes_response.content)

    audio_info = ffprobe_info(audio_path)
    video_info = ffprobe_info(video_path)
    record["audio_file"] = {
        "path": str(audio_path.relative_to(PROJECT_ROOT)),
        "size_bytes": len(audio_bytes_response.content),
        "sha256": _sha256_of(audio_path),
        **audio_info,
    }
    record["video_file"] = {
        "path": str(video_path.relative_to(PROJECT_ROOT)),
        "size_bytes": len(video_bytes_response.content),
        "sha256": _sha256_of(video_path),
        **video_info,
    }

    av_diff = None
    if audio_info.get("ok") and video_info.get("ok"):
        av_diff = abs(audio_info["duration_seconds"] - video_info["duration_seconds"])
    record["av_diff_seconds"] = round(av_diff, 3) if av_diff is not None else None

    record["checks"] = {
        "audio_duration_in_range": bool(
            audio_info.get("ok") and MEDIA_DURATION_MIN_SECONDS <= audio_info["duration_seconds"] <= MEDIA_DURATION_MAX_SECONDS
        ),
        "video_duration_in_range": bool(
            video_info.get("ok") and MEDIA_DURATION_MIN_SECONDS <= video_info["duration_seconds"] <= MEDIA_DURATION_MAX_SECONDS
        ),
        "av_diff_within_threshold": av_diff is not None and av_diff <= AV_DIFF_MAX_SECONDS,
        "video_codec_h264": video_info.get("video_codec") == "h264",
        "audio_codec_aac_or_mp3": video_info.get("audio_codec") in ("aac",) or audio_info.get("audio_codec") in ("mp3", "mp3float"),
    }
    record["all_checks_pass"] = all(record["checks"].values())
    return record


def _scan_log_for_errors(log_path: Path) -> list[str]:
    if not log_path.exists():
        return ["log file not found -- server logging was not captured to a file"]
    findings = []
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for marker in ("Traceback (most recent call last)", " ERROR ", "CRITICAL"):
        if marker in text:
            findings.append(marker.strip())
    return findings


async def wait_for_health(client: httpx.AsyncClient) -> None:
    for _ in range(30):
        try:
            response = await client.get("/health", timeout=2.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(0.5)
    raise RuntimeError("Trial server never reported healthy")


def _write_evidence(evidence: dict[str, Any], run_id: str) -> Path:
    evidence_path = EVIDENCE_DIR / f"gate-b-{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return evidence_path


async def main(smoke_test: bool, runs: int | None = None, skip_samples: bool = False) -> int:
    TRIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    n_b1_runs = runs if runs is not None else (1 if smoke_test else 5)
    # A trial that did not run the full declared matrix can never produce a real Gate B
    # PASS -- it is reported as DIAGNOSTIC_ONLY so a partial run can never be mistaken
    # for (or quoted as) a gate result.
    diagnostic_only = smoke_test or n_b1_runs < 5 or skip_samples
    evidence: dict[str, Any] = {
        "run_id": run_id,
        "started_at": _utc_now_iso(),
        "smoke_test": smoke_test,
        "diagnostic_only": diagnostic_only,
        "b1_runs_requested": n_b1_runs,
        "samples_skipped": skip_samples,
        "ai_mode": os.environ["DIE_AI_MODE"],
        "data_dir": str(TRIAL_DATA_DIR),
        "crashed": False,
    }

    print(f"[gate-b] starting trial server (AI_MODE={os.environ['DIE_AI_MODE']}, data_dir={TRIAL_DATA_DIR})", flush=True)
    server, base_url, port = _start_live_server()
    evidence["server_base_url"] = base_url
    print(f"[gate-b] server up at {base_url}", flush=True)

    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(30.0, read=1500.0)) as client:
            await wait_for_health(client)

            health_response = await client.get("/api/ai/health")
            evidence["ai_health_at_start"] = health_response.json()["data"]
            print(f"[gate-b] /api/ai/health: {evidence['ai_health_at_start']}", flush=True)

            b1_eight_min_runs: list[dict] = []
            for i in range(n_b1_runs):
                print(f"[gate-b] B1 8-minute run {i + 1}/{n_b1_runs} starting...", flush=True)
                duration = 2.0 if smoke_test else 8.0
                record = await run_script_trial(client, "B1", duration, f"b1-8min-run{i + 1}")
                b1_eight_min_runs.append(record)
                evidence["b1_eight_minute_runs"] = b1_eight_min_runs
                _write_evidence(evidence, run_id)  # incremental save -- survives a later crash
                print(
                    f"[gate-b] B1 8-minute run {i + 1}/{n_b1_runs}: status={record['job_status']} "
                    f"seconds={record['total_seconds']} words={(record['content'] or {}).get('total_words')}",
                    flush=True,
                )

            passing_runs = [
                r for r in b1_eight_min_runs
                if r["job_status"] == "complete" and r["content"] and r["content"]["all_checks_pass"]
            ]
            evidence["b1_eight_minute_pass_count"] = len(passing_runs)
            evidence["b1_eight_minute_complete_count"] = sum(1 for r in b1_eight_min_runs if r["job_status"] == "complete")

            sample_runs: list[dict] = []
            if not smoke_test and not skip_samples:
                for cefr, minutes, label in (("B1", 5.0, "b1-5min"), ("B1", 10.0, "b1-10min"), ("A2", 8.0, "a2-8min"), ("C1", 8.0, "c1-8min")):
                    print(f"[gate-b] sample run {label} starting...", flush=True)
                    record = await run_script_trial(client, cefr, minutes, label)
                    sample_runs.append(record)
                    evidence["sample_runs"] = sample_runs
                    _write_evidence(evidence, run_id)
                    print(f"[gate-b] sample run {label}: status={record['job_status']} seconds={record['total_seconds']}", flush=True)
            evidence["sample_runs"] = sample_runs

            learning_runs: list[dict] = []
            source_projects = [r["project_id"] for r in b1_eight_min_runs if r["job_status"] == "complete"]
            n_learning = 1 if smoke_test else min(5, len(source_projects))
            for project_id in source_projects[:n_learning]:
                print(f"[gate-b] learning generation for project {project_id} starting...", flush=True)
                record = await run_learning_trial(client, project_id)
                learning_runs.append(record)
                evidence["learning_runs"] = learning_runs
                _write_evidence(evidence, run_id)
                print(f"[gate-b] learning for {project_id}: status={record['job_status']}", flush=True)
            evidence["learning_pass_count"] = sum(
                1 for r in learning_runs if r["job_status"] == "complete" and r.get("spot_check_pass")
            )

            media_pipeline: dict | None = None
            if passing_runs:
                winning_project_id = passing_runs[0]["project_id"]
                print(f"[gate-b] running real media pipeline for winning project {winning_project_id}...", flush=True)
                media_pipeline = await run_media_pipeline(client, winning_project_id, EVIDENCE_DIR)
                print(f"[gate-b] media pipeline checks: {media_pipeline['checks']}", flush=True)
            evidence["media_pipeline"] = media_pipeline

    except Exception as exc:  # noqa: BLE001 -- a multi-hour real trial must never lose evidence to an unhandled crash
        evidence["crashed"] = True
        evidence["crash_error"] = f"{type(exc).__name__}: {exc}"
        print(f"[gate-b] CRASHED: {evidence['crash_error']}", flush=True)
    finally:
        _stop_live_server(server)
        print("[gate-b] server stopped", flush=True)

    evidence["finished_at"] = _utc_now_iso()

    b1_pass_count = evidence.get("b1_eight_minute_pass_count", 0)
    b1_complete_count = evidence.get("b1_eight_minute_complete_count", 0)
    learning_runs_list = evidence.get("learning_runs", [])
    learning_pass_count = evidence.get("learning_pass_count", 0)
    media_pipeline_result = evidence.get("media_pipeline")

    decision_reasons: list[str] = []
    if evidence["crashed"]:
        decision_reasons.append(f"Runner crashed before completing: {evidence['crash_error']}")

    script_gate_pass = b1_complete_count == n_b1_runs and b1_pass_count >= (1 if smoke_test else B1_EIGHT_MIN_PASS_THRESHOLD)
    if not script_gate_pass:
        decision_reasons.append(
            f"B1 8-minute script gate: {b1_pass_count}/{n_b1_runs} passed content checks "
            f"({b1_complete_count}/{n_b1_runs} completed) -- needed "
            f"{'1/1 (smoke test)' if smoke_test else '4/5'}."
        )
    learning_gate_pass = len(learning_runs_list) > 0 and learning_pass_count == len(learning_runs_list)
    if not learning_gate_pass:
        decision_reasons.append(f"Learning gate: {learning_pass_count}/{len(learning_runs_list)} passed.")
    media_gate_pass = bool(media_pipeline_result and media_pipeline_result.get("all_checks_pass"))
    if not media_gate_pass:
        decision_reasons.append("Media pipeline: not run or failed one of the duration/A-V/codec checks.")

    overall_pass = (
        script_gate_pass and learning_gate_pass and media_gate_pass
        and not diagnostic_only and not evidence["crashed"]
    )
    if diagnostic_only and not evidence["crashed"]:
        evidence["decision"] = "DIAGNOSTIC_ONLY"
    else:
        evidence["decision"] = "PASS" if overall_pass else "FAIL"
    evidence["decision_reasons"] = decision_reasons if decision_reasons else ["all declared thresholds met"]

    # Per-section outcome summary: the Gate B post-mortem showed a job-level pass rate
    # alone hides *why* -- one section missing its word budget hard-fails the whole job,
    # so the per-job number understates per-section reliability.
    section_failures = [
        r for r in evidence.get("b1_eight_minute_runs", []) + evidence.get("sample_runs", [])
        if r["job_status"] == "error" and "word count" in (r.get("error_message") or "")
    ]
    other_failures = [
        r for r in evidence.get("b1_eight_minute_runs", []) + evidence.get("sample_runs", [])
        if r["job_status"] == "error" and "word count" not in (r.get("error_message") or "")
    ]
    evidence["failure_breakdown"] = {
        "section_word_count_failures": len(section_failures),
        "other_failures": len(other_failures),
        "other_failure_messages": [r.get("error_message") for r in other_failures],
    }

    evidence_path = _write_evidence(evidence, run_id)
    print(f"[gate-b] evidence written to {evidence_path}", flush=True)
    print(f"[gate-b] DECISION: {evidence['decision']}", flush=True)
    for reason in evidence["decision_reasons"]:
        print(f"[gate-b]   - {reason}", flush=True)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true", help="Run a fast abbreviated sanity check, not full Gate B.")
    parser.add_argument(
        "--mode", default="local",
        help="AI_MODE for the trial. 'local' (default) is Gate B's own fallback-OFF requirement; "
             "'gemini' runs the provider-comparison diagnostic.",
    )
    parser.add_argument(
        "--runs", type=int, default=None,
        help="Override the number of primary B1-eight-minute runs (default 5). Use a smaller "
             "number for a quota-bounded diagnostic; a run count below 5 can never produce a "
             "real Gate B PASS and is reported as DIAGNOSTIC_ONLY.",
    )
    parser.add_argument(
        "--skip-samples", action="store_true",
        help="Skip the B1 5/10-minute and A2/C1 sample runs (diagnostic use, saves quota).",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.smoke_test, runs=args.runs, skip_samples=args.skip_samples)))
