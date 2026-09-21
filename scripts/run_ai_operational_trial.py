"""Real no-mock operational trial and Gate B / Gate B-2 decision runner
(Phase 13 Task 13.9; extended for Phase 14 Task 14.4 -- "Gate B-2", the
re-run of Gate B under the 14.1/14.2/14.3 resilience changes).

Drives a real in-process `uvicorn` server (same pattern as `record_demo_video.py` and
the browser test suite's `live_server_url` fixture) over real HTTP via `httpx` --
never `fastapi.testclient.TestClient`, never a mocked provider. `DIE_AI_MODE` is set
before any `app.*` import so the mode is genuinely in effect for the whole trial, per
Gate B's own "fallback OFF" requirement for the local matrix. Local inference is real
Ollama/qwen3.5:9b (already qualified in Task 13.1's Gate A); learning generation and
the final audio/video pipeline are likewise driven only through the real running app.

Evidence for a fresh (Phase 14 / Gate B-2) run lands under
`data/quality_reviews/phase14/gate-b2/` (gitignored via the existing
`data/quality_reviews/` entry -- the controlling plan's literal
`artifacts/phase13/gate-b/`-style path is not gitignored and `.gitignore` is not in
this task's allowed files, matching the same deviation Task 13.1 already made for Gate
A). The Phase 13 Gate B evidence this file replaced stays at its own
`data/quality_reviews/phase13/gate-b/` path -- `--reaggregate` reads a file's own
recorded `data_dir` to find the right trial DB regardless of which phase it came from.

Usage:
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --matrix local
        # Gate B-2 local matrix (13.9 protocol verbatim)
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --matrix gemini --with-samples --with-media
        # Gate B-2 Gemini matrix, full protocol
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --matrix gemini --runs 3
        # first half of a quota-split Gemini matrix
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --matrix gemini --resume-evidence <day1.json>
        # second half, merging with the first
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --reaggregate <evidence.json>
        # recompute classification/aggregates/decision from an existing evidence file;
        # no server, no network, no live trial
    venv\\Scripts\\python scripts\\run_ai_operational_trial.py --smoke-test
        # fast sanity check (legacy path, unchanged)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import socket
import sqlite3
import statistics
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

TRIAL_DATA_DIR = PROJECT_ROOT / "data" / "quality_reviews" / "phase14" / "gate-b2" / "trial-data"
EVIDENCE_DIR = PROJECT_ROOT / "data" / "quality_reviews" / "phase14" / "gate-b2"

# Must be set before any `app.*` import -- Settings() is a module-level singleton
# read from the environment once, at import time. argparse runs too late for that,
# so the mode is read straight off sys.argv here.
#
# `local` is Gate B's own requirement (fallback OFF) and stays the default. `--mode
# gemini` exists only for the provider-comparison diagnostic that the 2026-09-21 Gate B
# post-mortem asked for: the ±15%-per-section validator applies to *every* provider, so
# "does the primary provider clear the same bar?" had to be measurable, not assumed.
#
# Task 14.4a: `--matrix {local,gemini}` is the Gate B-2 way to select this (it also
# picks the decision-rule-set and default sample/media behaviour, not just the env
# var) -- but an explicit `--mode` still wins over it, for the raw-diagnostic escape
# hatch the task card asks to keep. Neither flag existing at all (a bare rerun of an
# older invocation) reproduces the exact old default.
_MODE = "local"
if "--matrix" in sys.argv:
    _MODE = sys.argv[sys.argv.index("--matrix") + 1]
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


# Task 14.4a: the Phase 13 report disclosed a false negative here -- a natural
# closing line ("Good luck with your journey to better health and longer life
# ahead.", from the one completed local run in gate-b-20260921T000903Z.json)
# matched none of the old marker list below. Widened it with a few more common
# closing phrases, and -- since the outline's own last-section objective reliably
# states its intent ("The interviewer concludes the show by summarizing key
# takeaways...") even when the generated line's exact wording doesn't echo any
# marker -- `_has_outro` also treats the objective as a signal. "conclu" is a
# deliberate substring match (catches "concludes"/"concluding"/"conclusion").
_OUTRO_LINE_MARKERS = (
    "thanks for", "thank you for", "see you", "that's all", "goodbye", "bye",
    "until next", "take care", "good luck", "all the best", "wrap up",
    "wrapping up", "before we go", "that wraps",
)
_OUTRO_OBJECTIVE_MARKERS = ("closing", "outro", "farewell", "conclu", "wrap up", "sign off", "signing off")


def _has_outro(last_text_lower: str, outline_last_objective: str | None) -> bool:
    """See the module comment above `_OUTRO_LINE_MARKERS` for why this exists."""
    if any(marker in last_text_lower for marker in _OUTRO_LINE_MARKERS):
        return True
    if outline_last_objective:
        objective_lower = outline_last_objective.lower()
        if any(marker in objective_lower for marker in _OUTRO_OBJECTIVE_MARKERS):
            return True
    return False


def analyze_script(
    lines: list[dict], known_speaker_ids: set[str], outline_last_objective: str | None = None
) -> dict[str, Any]:
    """Independent, runner-side content check -- deliberately does not reuse
    script_pipeline.py's own validators, since Gate B measures the outcome, not
    re-trusts the code under test.

    `outline_last_objective` (Task 14.4a): the outline's own last-section
    `objective` text, when available (read from the trial DB), used only to
    widen the `has_outro` false-negative fix below -- see `_has_outro`.
    """
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
    has_intro = any(marker in first_text for marker in intro_markers)
    has_outro = _has_outro(last_text, outline_last_objective)

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


# --- Task 14.4a: failure classification, call telemetry, per-section reads -----------

_CONTENT_ERROR_CODES = frozenset(
    {"section_validation_failed", "global_validation_failed", "schema_validation_failed"}
)


def classify_failure(error_code: str | None, error_message: str | None) -> str:
    """`infra`/`content`/`other`, from a job's Task 14.2 `error_code` (plan §4.4/§6
    Amendment B). `error_message` is accepted but currently unused -- kept in the
    signature since a human reading a printed `other` classification wants the
    message right next to the call, and future callers may want to sniff it too.
    `infra`: `error_code` starts with `"provider_"`. `content`:
    `section_validation_failed` / `global_validation_failed` /
    `schema_validation_failed`. `other`: everything else, including
    `handler_exception` and pre-14.2 evidence with no real `error_code` at all --
    exactly how the two named Phase 13 files classify (see task-14.4.md)."""
    del error_message  # not used for classification itself; see docstring
    if error_code and error_code.startswith("provider_"):
        return "infra"
    if error_code in _CONTENT_ERROR_CODES:
        return "content"
    return "other"


def _empty_call_stats() -> dict[str, Any]:
    return {
        "total_calls": 0,
        "total_attempts": 0,
        "total_backoff_seconds": 0.0,
        "max_attempts_on_one_call": 0,
        "absorbed_transient_errors": 0,
        "error_calls": 0,
    }


def call_stats(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize one job's `metrics.calls[]` (Task 14.2's `AIJobOut.metrics`).

    Only `outcome == "ok"` calls carry `attempts`/`backoff_seconds` -- an
    `outcome == "error"` call's exception is raised before a `GenerationResult`
    exists to read those from (see `script_pipeline._call_record`), so they are
    excluded from the attempt/backoff aggregates rather than silently counted
    as zero-attempt calls.
    """
    if not calls:
        return _empty_call_stats()
    ok_calls = [c for c in calls if c.get("outcome") == "ok"]
    attempts = [c.get("attempts") or 0 for c in ok_calls]
    return {
        "total_calls": len(calls),
        "total_attempts": sum(attempts),
        "total_backoff_seconds": round(sum(c.get("backoff_seconds") or 0.0 for c in ok_calls), 2),
        "max_attempts_on_one_call": max(attempts, default=0),
        "absorbed_transient_errors": sum(max(a - 1, 0) for a in attempts),
        "error_calls": len(calls) - len(ok_calls),
    }


def _trial_db_path(evidence: dict[str, Any] | None = None) -> Path:
    """The trial's SQLite file to read checkpoint-level data from. A live run
    always uses the *current* `TRIAL_DATA_DIR`; `--reaggregate` instead trusts
    the evidence file's own recorded `data_dir` field, since older evidence
    (e.g. the two named Phase 13 files) points at a different location than
    this script's current default."""
    if evidence and evidence.get("data_dir"):
        return Path(evidence["data_dir"]) / "app.db"
    return TRIAL_DATA_DIR / "app.db"


def _open_trial_db(db_path: Path) -> sqlite3.Connection | None:
    """A short-lived connection with a generous busy timeout, tolerating the
    live server's own concurrent writes. Returns `None` (never raises) if the
    file doesn't exist or can't be opened -- a diagnostic read must never crash
    the run it's trying to report on, and `--reaggregate` against an evidence
    file whose trial DB is gone should degrade to an empty table, not fail."""
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error:
        return None


def read_section_checkpoints(job_id: str, db_path: Path) -> list[dict[str, Any]]:
    """Best-effort read of one job's `stage='section'` checkpoints straight from
    the trial's own SQLite file. `AIJobOut` deliberately never exposes
    checkpoint-level data (see `app/models/ai_job.py`'s own docstring) -- this is
    a diagnostic runner, not the running app, and is allowed to look deeper."""
    conn = _open_trial_db(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT section_index, metrics_json FROM ai_generation_checkpoints "
            "WHERE job_id = ? AND stage = 'section' ORDER BY section_index",
            (job_id,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    sections = []
    for row in rows:
        try:
            metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
        except (TypeError, ValueError):
            metrics = {}
        if not isinstance(metrics, dict):
            metrics = {}
        sections.append({"section_index": row["section_index"], **metrics})
    return sections


def read_outline_last_objective(job_id: str, db_path: Path) -> str | None:
    """The outline's own last-section `objective` text, for the `has_outro`
    fallback in `_has_outro` -- read from the same trial SQLite file."""
    conn = _open_trial_db(db_path)
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT result_json FROM ai_generation_checkpoints WHERE job_id = ? AND stage = 'outline'",
            (job_id,),
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    if row is None or not row["result_json"]:
        return None
    try:
        outline = json.loads(row["result_json"])
        sections = outline.get("sections") or []
        return sections[-1]["objective"] if sections else None
    except (TypeError, ValueError, KeyError, IndexError):
        return None


async def run_script_trial(client: httpx.AsyncClient, cefr_level: str, duration_minutes: float, label: str) -> dict:
    project = await create_project(client, cefr_level, duration_minutes, label)
    known_speaker_ids = {s["id"] for s in project["speakers"]}
    result = await create_and_wait_job(client, project["id"], "script")
    job = result["job"]
    metrics = job.get("metrics") or {}
    db_path = _trial_db_path()

    record: dict[str, Any] = {
        "label": label,
        "cefr_level": cefr_level,
        "duration_minutes": duration_minutes,
        "project_id": project["id"],
        "job_id": result["job_id"],
        "job_status": job["status"],
        "error_code": job.get("error_code"),
        "error_message": job.get("error_message"),
        "failure_class": classify_failure(job.get("error_code"), job.get("error_message"))
        if job["status"] == "error"
        else None,
        "actual_provider": job.get("actual_provider"),
        "model": job.get("model"),
        "fallback_used": job.get("fallback_used"),
        "fallback_count": job.get("fallback_count"),
        "repair_count": job.get("repair_count"),
        "recovery_count": job.get("recovery_count"),
        "metrics": metrics,
        "call_stats": call_stats(metrics.get("calls") or []),
        "sections": read_section_checkpoints(result["job_id"], db_path),
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
        outline_last_objective = read_outline_last_objective(result["job_id"], db_path)
        record["content"] = analyze_script(lines, known_speaker_ids, outline_last_objective)
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


# --- Task 14.4a: matrix aggregates and the Gemini-specific decision rule -------------


def compute_matrix_aggregates(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Plan §4.4 "Aggregate per provider" list, computed over a list of
    per-run records shaped like `run_script_trial`'s return value (works
    identically for a fresh run's records and an old evidence file's, for
    `--reaggregate` -- every field is read with `.get(...)`, never assumed
    present)."""
    n = len(runs)
    completed = [r for r in runs if r.get("job_status") == "complete"]
    content_pass = [r for r in completed if (r.get("content") or {}).get("all_checks_pass")]
    infra_failures = [r for r in runs if r.get("failure_class") == "infra"]
    handler_exceptions = [r for r in runs if r.get("error_code") == "handler_exception"]

    all_sections = [s for r in runs for s in (r.get("sections") or [])]
    sections_with_data = [s for s in all_sections if "target_nominal" in s and "words" in s]
    deviations_vs_nominal: list[float] = []
    within_15pct_of_nominal = 0
    for section in sections_with_data:
        nominal = section.get("target_nominal")
        words = section.get("words")
        if not nominal:
            continue
        deviation = (words - nominal) / nominal
        deviations_vs_nominal.append(deviation)
        if abs(deviation) <= 0.15:
            within_15pct_of_nominal += 1

    repaired_sections = [s for s in sections_with_data if s.get("repaired")]
    repair_successes = 0
    for section in repaired_sections:
        effective = section.get("target_effective")
        words = section.get("words")
        if effective and abs((words - effective) / effective) <= 0.15:
            repair_successes += 1

    totals = [r["content"]["total_words"] for r in completed if r.get("content")]
    totals_in_range = sum(1 for total in totals if WORD_COUNT_MIN <= total <= WORD_COUNT_MAX)

    total_backoff = sum((r.get("call_stats") or {}).get("total_backoff_seconds", 0.0) for r in runs)
    max_attempts = max(
        ((r.get("call_stats") or {}).get("max_attempts_on_one_call", 0) for r in runs), default=0
    )

    return {
        "n_runs": n,
        "completion_rate": round(len(completed) / n, 4) if n else None,
        "content_pass_rate": round(len(content_pass) / len(completed), 4) if completed else None,
        "infra_failure_count": len(infra_failures),
        "handler_exception_count": len(handler_exceptions),
        "per_section_sample_size": len(sections_with_data),
        "per_section_within_15pct_of_nominal_rate": (
            round(within_15pct_of_nominal / len(sections_with_data), 4) if sections_with_data else None
        ),
        "repair_sample_size": len(repaired_sections),
        "repair_success_rate": (
            round(repair_successes / len(repaired_sections), 4) if repaired_sections else None
        ),
        "mean_section_deviation_pct_vs_nominal": (
            round(statistics.fmean(deviations_vs_nominal), 4) if deviations_vs_nominal else None
        ),
        "stdev_section_deviation_pct_vs_nominal": (
            round(statistics.pstdev(deviations_vs_nominal), 4) if len(deviations_vs_nominal) > 1 else None
        ),
        "totals_sample_size": len(totals),
        "totals_in_720_880_count": totals_in_range,
        "total_repair_count": sum(r.get("repair_count") or 0 for r in runs),
        "total_fallback_count": sum(r.get("fallback_count") or 0 for r in runs),
        "total_backoff_seconds": round(total_backoff, 2),
        "max_attempts_observed": max_attempts,
    }


def local_matrix_decision(runs: list[dict[str, Any]], n_requested: int, smoke_test: bool) -> tuple[str, list[str]]:
    """The Phase 13 Gate B rule verbatim (plan §4.4: "PASS promotes local in
    development"). This is the script-completion/content-pass gate only --
    the caller still folds in the learning/media gates and `diagnostic_only`,
    matching Task 13.9's original combined decision exactly."""
    completed = [r for r in runs if r.get("job_status") == "complete"]
    content_pass = [r for r in completed if (r.get("content") or {}).get("all_checks_pass")]
    threshold = 1 if smoke_test else B1_EIGHT_MIN_PASS_THRESHOLD
    script_gate_pass = len(completed) == n_requested and len(content_pass) >= threshold
    reasons: list[str] = []
    if not script_gate_pass:
        reasons.append(
            f"B1 8-minute script gate: {len(content_pass)}/{n_requested} passed content checks "
            f"({len(completed)}/{n_requested} completed) -- needed "
            f"{'1/1 (smoke test)' if smoke_test else f'{B1_EIGHT_MIN_PASS_THRESHOLD}/5'}."
        )
    return ("PASS" if script_gate_pass else "FAIL"), reasons


def gemini_matrix_decision(runs: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """Plan §4.4's Gemini decision rule: `PASS-cloud` = 5/5 complete AND >=4/5
    content pass AND <=1 infra job death. Absorbed transient errors (retries
    that ended `ok`, Task 14.1's own success signal) are never counted as
    failures here -- only a job that actually *died* with an `infra`-classified
    `error_code` counts. >=2 infra deaths -> `FAIL-INFRA` (reopens Task 14.1,
    blocks 14.6 again). Content failures alone -> `FAIL-CONTENT`. Any
    `handler_exception` is flagged as a defect requiring triage regardless of
    which decision the numbers alone would produce."""
    n = len(runs)
    completed = [r for r in runs if r.get("job_status") == "complete"]
    content_pass = [r for r in completed if (r.get("content") or {}).get("all_checks_pass")]
    infra_deaths = [r for r in runs if r.get("failure_class") == "infra"]
    handler_exceptions = [r for r in runs if r.get("error_code") == "handler_exception"]

    reasons: list[str] = []
    if handler_exceptions:
        reasons.append(
            f"{len(handler_exceptions)} handler_exception(s) -- defect triage required before "
            "quoting this matrix (plan §4.4)."
        )

    if len(completed) == 5 and len(content_pass) >= 4 and len(infra_deaths) <= 1:
        decision = "PASS-cloud"
        if infra_deaths:
            reasons.append(
                f"{len(infra_deaths)} infra job death absorbed within the <=1 allowance "
                f"({', '.join(r.get('label', r.get('job_id', '?')) for r in infra_deaths)})."
            )
    elif len(infra_deaths) >= 2:
        decision = "FAIL-INFRA"
        reasons.append(f"{len(infra_deaths)} infra job deaths (>=2 threshold) -- reopens Task 14.1.")
    else:
        decision = "FAIL-CONTENT"
        reasons.append(
            f"{len(content_pass)}/{len(completed)} passed content checks ({len(completed)}/{n} completed)."
        )
    if not reasons:
        reasons.append("all declared thresholds met")
    return decision, reasons


def _write_evidence(evidence: dict[str, Any], run_id: str) -> Path:
    evidence_path = EVIDENCE_DIR / f"gate-b2-{run_id}.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return evidence_path


async def main(
    smoke_test: bool,
    runs: int | None = None,
    skip_samples: bool = False,
    matrix: str | None = None,
    with_samples: bool = False,
    with_media: bool = False,
    resume_evidence: str | None = None,
) -> int:
    TRIAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    n_b1_runs = runs if runs is not None else (1 if smoke_test else 5)

    # Task 14.4a: `--matrix gemini` defaults samples/media OFF (opt in via
    # `--with-samples`/`--with-media`, plan §4.4 item 5); `--matrix local` (or no
    # `--matrix` at all, the legacy/raw-diagnostic path) keeps the exact Task 13.9
    # behaviour -- samples/media run unconditionally unless explicitly skipped.
    if matrix == "gemini":
        run_samples = with_samples and not smoke_test
        run_media = with_media
    else:
        run_samples = not smoke_test and not skip_samples
        run_media = True

    # Task 14.4a `--resume-evidence`: seed already-completed runs from a prior
    # evidence file (a quota-split Gemini matrix run across two calendar days)
    # so only the remaining B1-eight-minute runs actually execute this time.
    b1_eight_min_runs: list[dict] = []
    sample_runs: list[dict] = []
    learning_runs: list[dict] = []
    resumed_from: str | None = None
    if resume_evidence:
        prior = json.loads(Path(resume_evidence).read_text(encoding="utf-8"))
        b1_eight_min_runs = list(prior.get("b1_eight_minute_runs", []))
        sample_runs = list(prior.get("sample_runs", []))
        learning_runs = list(prior.get("learning_runs", []))
        resumed_from = str(resume_evidence)
        print(
            f"[gate-b] resumed from {resume_evidence}: {len(b1_eight_min_runs)} B1 run(s) "
            f"already recorded, {max(0, n_b1_runs - len(b1_eight_min_runs))} remaining",
            flush=True,
        )

    # A trial that did not run the full declared matrix can never produce a real Gate B
    # PASS -- it is reported as DIAGNOSTIC_ONLY so a partial run can never be mistaken
    # for (or quoted as) a gate result. For the Gemini matrix, samples/media are
    # optional by design (item 5), so they never make an otherwise-complete 5-run
    # matrix diagnostic-only; for the local matrix they still must run (13.9 parity).
    if matrix == "gemini":
        diagnostic_only = smoke_test or n_b1_runs < 5
    else:
        diagnostic_only = smoke_test or n_b1_runs < 5 or skip_samples
    evidence: dict[str, Any] = {
        "run_id": run_id,
        "started_at": _utc_now_iso(),
        "smoke_test": smoke_test,
        "diagnostic_only": diagnostic_only,
        "matrix": matrix,
        "b1_runs_requested": n_b1_runs,
        "samples_skipped": skip_samples,
        "samples_run": run_samples,
        "media_run": run_media,
        "resumed_from": resumed_from,
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

            remaining_b1_runs = max(0, n_b1_runs - len(b1_eight_min_runs))
            for i in range(remaining_b1_runs):
                run_number = len(b1_eight_min_runs) + 1
                print(f"[gate-b] B1 8-minute run {run_number}/{n_b1_runs} starting...", flush=True)
                duration = 2.0 if smoke_test else 8.0
                record = await run_script_trial(client, "B1", duration, f"b1-8min-run{run_number}")
                b1_eight_min_runs.append(record)
                evidence["b1_eight_minute_runs"] = b1_eight_min_runs
                _write_evidence(evidence, run_id)  # incremental save -- survives a later crash
                print(
                    f"[gate-b] B1 8-minute run {run_number}/{n_b1_runs}: status={record['job_status']} "
                    f"seconds={record['total_seconds']} words={(record['content'] or {}).get('total_words')}",
                    flush=True,
                )

            passing_runs = [
                r for r in b1_eight_min_runs
                if r["job_status"] == "complete" and r["content"] and r["content"]["all_checks_pass"]
            ]
            evidence["b1_eight_minute_pass_count"] = len(passing_runs)
            evidence["b1_eight_minute_complete_count"] = sum(1 for r in b1_eight_min_runs if r["job_status"] == "complete")

            if run_samples and not sample_runs:
                for cefr, minutes, label in (("B1", 5.0, "b1-5min"), ("B1", 10.0, "b1-10min"), ("A2", 8.0, "a2-8min"), ("C1", 8.0, "c1-8min")):
                    print(f"[gate-b] sample run {label} starting...", flush=True)
                    record = await run_script_trial(client, cefr, minutes, label)
                    sample_runs.append(record)
                    evidence["sample_runs"] = sample_runs
                    _write_evidence(evidence, run_id)
                    print(f"[gate-b] sample run {label}: status={record['job_status']} seconds={record['total_seconds']}", flush=True)
            evidence["sample_runs"] = sample_runs

            source_projects = [r["project_id"] for r in b1_eight_min_runs if r["job_status"] == "complete"]
            n_learning = 1 if smoke_test else min(5, len(source_projects))
            already_run_projects = {r["project_id"] for r in learning_runs}
            for project_id in source_projects[:n_learning]:
                if project_id in already_run_projects:
                    continue
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
            if run_media and passing_runs:
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
    evidence["aggregates"] = compute_matrix_aggregates(evidence.get("b1_eight_minute_runs", []))

    if matrix == "gemini":
        gemini_decision, gemini_reasons = gemini_matrix_decision(evidence.get("b1_eight_minute_runs", []))
        if evidence["crashed"]:
            gemini_reasons = [f"Runner crashed before completing: {evidence['crash_error']}", *gemini_reasons]
        if diagnostic_only:
            evidence["decision"] = "DIAGNOSTIC_ONLY"
            evidence["decision_reasons"] = [f"partial matrix ({n_b1_runs} B1 runs requested, need 5)", *gemini_reasons]
        else:
            evidence["decision"] = gemini_decision
            evidence["decision_reasons"] = gemini_reasons
        evidence_path = _write_evidence(evidence, run_id)
        print(f"[gate-b] evidence written to {evidence_path}", flush=True)
        print(f"[gate-b] DECISION: {evidence['decision']}", flush=True)
        for reason in evidence["decision_reasons"]:
            print(f"[gate-b]   - {reason}", flush=True)
        return 0

    learning_runs_list = evidence.get("learning_runs", [])
    learning_pass_count = evidence.get("learning_pass_count", 0)
    media_pipeline_result = evidence.get("media_pipeline")

    decision_reasons: list[str] = []
    if evidence["crashed"]:
        decision_reasons.append(f"Runner crashed before completing: {evidence['crash_error']}")

    # Task 14.4a: this now calls the shared `local_matrix_decision` (plan §4.4's
    # "Phase 13 Gate B rule verbatim") instead of duplicating the formula inline;
    # same thresholds, same message text -- b1_pass_count/b1_complete_count above
    # stay only for the per-run print lines already emitted during the loop.
    script_decision, script_gate_reasons = local_matrix_decision(
        evidence.get("b1_eight_minute_runs", []), n_b1_runs, smoke_test
    )
    script_gate_pass = script_decision == "PASS"
    if not script_gate_pass:
        decision_reasons.extend(script_gate_reasons)
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


# --- Task 14.4a: --reaggregate (no server, no network, no live trial) ---------------


def reaggregate(evidence_path: Path) -> int:
    """Recompute failure classification, matrix aggregates, and the matrix
    decision from an existing evidence file -- never starts a server or makes
    a network call. This is the Coder's own verification mechanism for this
    task (task-14.4.md: "Coder never runs a live trial") and is also how a
    quota-split Gemini matrix's two evidence files get checked individually
    before `--resume-evidence` merges them into one live run's decision.
    """
    data = json.loads(evidence_path.read_text(encoding="utf-8"))
    runs = list(data.get("b1_eight_minute_runs", []))
    db_path = _trial_db_path(data)

    for run in runs:
        run["failure_class"] = (
            classify_failure(run.get("error_code"), run.get("error_message"))
            if run.get("job_status") == "error"
            else None
        )
        if not run.get("sections"):
            run["sections"] = read_section_checkpoints(run.get("job_id") or "", db_path)
        if not run.get("call_stats"):
            run["call_stats"] = call_stats((run.get("metrics") or {}).get("calls") or [])

    aggregates = compute_matrix_aggregates(runs)
    ai_mode = data.get("ai_mode", "local")
    matrix = data.get("matrix") or ai_mode
    n_requested = data.get("b1_runs_requested", len(runs))
    smoke_test = bool(data.get("smoke_test"))
    diagnostic_only = bool(data.get("diagnostic_only")) or n_requested < 5

    if matrix == "gemini":
        decision, reasons = gemini_matrix_decision(runs)
        if diagnostic_only:
            reasons = [f"partial matrix ({n_requested} B1 runs requested, need 5)", *reasons]
            decision = "DIAGNOSTIC_ONLY"
    else:
        decision, reasons = local_matrix_decision(runs, n_requested, smoke_test)
        if diagnostic_only:
            decision = "DIAGNOSTIC_ONLY"

    print(f"[reaggregate] source: {evidence_path}")
    print(
        f"[reaggregate] ai_mode={ai_mode} matrix={matrix} b1_runs_requested={n_requested} "
        f"diagnostic_only={diagnostic_only}"
    )
    print("[reaggregate] per-run failure classification:")
    for run in runs:
        print(
            f"[reaggregate]   {run.get('label')}: status={run.get('job_status')} "
            f"error_code={run.get('error_code')!r} failure_class={run.get('failure_class')!r} "
            f"message={(run.get('error_message') or '')[:120]!r}"
        )
    print(f"[reaggregate] aggregates: {json.dumps(aggregates, indent=2)}")
    print(f"[reaggregate] DECISION: {decision}")
    for reason in reasons:
        print(f"[reaggregate]   - {reason}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true", help="Run a fast abbreviated sanity check, not full Gate B.")
    parser.add_argument(
        "--mode", default=None,
        help="Raw-diagnostic AI_MODE override ('local'/'gemini'/'hybrid'). Wins over --matrix "
             "for the actual DIE_AI_MODE env var if both are given, per task-14.4.md's "
             "'keep --mode for raw diagnostics' instruction.",
    )
    parser.add_argument(
        "--matrix", choices=("local", "gemini"), default=None,
        help="Gate B-2 matrix (Task 14.4): selects DIE_AI_MODE (unless --mode overrides it), "
             "which decision rule applies (13.9-verbatim for local, PASS-cloud/FAIL-INFRA/"
             "FAIL-CONTENT for gemini), and the default sample/media behaviour. Omit for the "
             "old ad-hoc --mode-only raw-diagnostic path (unchanged).",
    )
    parser.add_argument(
        "--runs", type=int, default=None,
        help="Override the number of primary B1-eight-minute runs (default 5). Use a smaller "
             "number for a quota-bounded diagnostic; a run count below 5 can never produce a "
             "real Gate B PASS and is reported as DIAGNOSTIC_ONLY.",
    )
    parser.add_argument(
        "--skip-samples", action="store_true",
        help="Local matrix / legacy path only: skip the B1 5/10-minute and A2/C1 sample runs "
             "(diagnostic use, saves quota). The Gemini matrix skips samples by default already "
             "-- use --with-samples there instead.",
    )
    parser.add_argument(
        "--with-samples", action="store_true",
        help="Gemini matrix only: also run the B1 5/10-min and A2/C1 samples (off by default "
             "for --matrix gemini, per plan §4.4 item 5's 'samples optional').",
    )
    parser.add_argument(
        "--with-media", action="store_true",
        help="Gemini matrix only: also run the real audio/video pipeline on the first passing "
             "run (off by default for --matrix gemini, per plan §4.4 item 5's 'media optional').",
    )
    parser.add_argument(
        "--resume-evidence", default=None, metavar="EVIDENCE_JSON",
        help="Seed already-completed B1/sample/learning runs from a prior evidence file and only "
             "run however many more B1-eight-minute runs are needed to reach --runs (default 5) "
             "-- for a Gemini matrix split across two calendar days (plan §4.4).",
    )
    parser.add_argument(
        "--reaggregate", default=None, metavar="EVIDENCE_JSON",
        help="Recompute failure classification, aggregates, and the matrix decision from an "
             "existing evidence file. No server, no network, no live trial.",
    )
    args = parser.parse_args()

    if args.reaggregate:
        sys.exit(reaggregate(Path(args.reaggregate)))

    sys.exit(asyncio.run(main(
        args.smoke_test,
        runs=args.runs,
        skip_samples=args.skip_samples,
        matrix=args.matrix,
        with_samples=args.with_samples,
        with_media=args.with_media,
        resume_evidence=args.resume_evidence,
    )))
