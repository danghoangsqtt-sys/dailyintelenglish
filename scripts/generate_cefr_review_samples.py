"""Generate traceable CEFR-by-genre script samples for human quality review."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.constants import (  # noqa: E402
    ACCENTS,
    CEFR_LEVELS,
    GEMINI_MODEL,
    GEMINI_RATE_LIMIT_RPM,
    GENRES,
)
from app.services import script_service  # noqa: E402
from app.services.script_service import ScriptLineOut  # noqa: E402

APPROVED_GENRES = ("small_talk", "interview", "news")
TOPICS_BY_GENRE = {
    "small_talk": "Planning a healthy weekday routine",
    "interview": "How remote work changes communication",
    "news": "A city opens a new public library",
}
ACCENT = "american"
DEFAULT_DURATION_MINUTES = 2.0
NUM_SPEAKERS = 2
REQUEST_INTERVAL_SECONDS = (60.0 / GEMINI_RATE_LIMIT_RPM) + 0.1
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "quality_reviews" / "script-samples"
LANGUAGE_FEATURES = {
    "collocation": True,
    "idiom": True,
    "slang": False,
    "local_expressions": False,
    "phrasal_verbs": True,
    "business_register": False,
}
SPEAKER_BLUEPRINTS = (
    {"name": "Alex", "gender": "male"},
    {"name": "Maya", "gender": "female"},
)

GenerateFunction = Callable[[str, dict[str, Any]], Awaitable[list[ScriptLineOut]]]
SleepFunction = Callable[[float], Awaitable[None]]
ClockFunction = Callable[[], float]


def _validate_static_contract() -> None:
    """Fail clearly if project constants drift away from the PM-approved matrix."""
    missing_levels = [level for level in CEFR_LEVELS if level not in ("A1", "A2", "B1", "B2", "C1", "C2")]
    if missing_levels or tuple(CEFR_LEVELS) != ("A1", "A2", "B1", "B2", "C1", "C2"):
        raise RuntimeError(f"Unexpected CEFR_LEVELS contract: {CEFR_LEVELS}")
    if any(genre not in GENRES for genre in APPROVED_GENRES):
        raise RuntimeError(f"Approved genre missing from GENRES: {APPROVED_GENRES}")
    if ACCENT not in ACCENTS:
        raise RuntimeError(f"Approved accent missing from ACCENTS: {ACCENT}")


def _positive_float(raw_value: str) -> float:
    """Parse a strictly positive command-line float."""
    value = float(raw_value)
    if value <= 0:
        raise argparse.ArgumentTypeError("duration must be greater than zero")
    return value


def _reject_duplicates(values: Sequence[str], label: str) -> None:
    """Reject duplicate selectors so each requested matrix case is unique."""
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label} values are not allowed")


def _speaker_config(name: str, gender: str) -> dict[str, Any]:
    """Build one production-shaped in-memory speaker config with a fresh UUID."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "gender": gender,
        "accent": ACCENT,
        "tts_engine": "edge_tts",
        "voice_description": "",
        "speed": 1.0,
        "pitch": 0.0,
        "volume": 1.0,
    }


def build_cases(
    levels: Sequence[str],
    genres: Sequence[str],
    duration_minutes: float,
) -> list[dict[str, Any]]:
    """Build the selected in-memory generation cases in deterministic matrix order."""
    _validate_static_contract()
    if not levels:
        raise ValueError("at least one CEFR level is required")
    if not genres:
        raise ValueError("at least one genre is required")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than zero")
    _reject_duplicates(levels, "CEFR level")
    _reject_duplicates(genres, "genre")

    unknown_levels = [level for level in levels if level not in CEFR_LEVELS]
    if unknown_levels:
        raise ValueError(f"unknown CEFR level(s): {', '.join(unknown_levels)}")
    unknown_genres = [genre for genre in genres if genre not in APPROVED_GENRES]
    if unknown_genres:
        raise ValueError(f"unapproved genre(s): {', '.join(unknown_genres)}")

    cases: list[dict[str, Any]] = []
    for level in levels:
        for genre in genres:
            project_id = str(uuid.uuid4())
            config = {
                "name": f"CEFR Review {level} {genre}",
                "topic": TOPICS_BY_GENRE[genre],
                "cefr_level": level,
                "genre": genre,
                "accent": ACCENT,
                "duration_minutes": duration_minutes,
                "num_speakers": NUM_SPEAKERS,
                "language_features": dict(LANGUAGE_FEATURES),
                "speakers": [
                    _speaker_config(blueprint["name"], blueprint["gender"])
                    for blueprint in SPEAKER_BLUEPRINTS
                ],
            }
            cases.append(
                {
                    "case_id": f"{level}__{genre}",
                    "project_id": project_id,
                    "config": config,
                    "status": "pending",
                    "output_file": None,
                    "line_count": None,
                    "error": None,
                }
            )
    return cases


def _new_manifest(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Create the traceability manifest before any provider call starts."""
    return {
        "task": "2.1a",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": GEMINI_MODEL,
        "request_interval_seconds": REQUEST_INTERVAL_SECONDS,
        "case_count": len(cases),
        "status": "running",
        "successful_cases": 0,
        "failed_cases": 0,
        "cases": cases,
    }


def _make_run_directory_sync(output_root: Path, run_id: str | None) -> Path:
    """Create one non-overwriting timestamped output directory."""
    resolved_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = output_root / resolved_run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "samples").mkdir()
    return run_dir


def _write_text_atomic_sync(path: Path, content: str) -> None:
    """Write UTF-8 text atomically so a checkpoint is never partially visible."""
    temporary_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def _write_json_atomic_sync(path: Path, payload: object) -> None:
    """Serialize JSON without ASCII-escaping and replace the target atomically."""
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text_atomic_sync(path, content)


async def _write_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Checkpoint the current manifest without blocking the event loop."""
    await asyncio.to_thread(_write_json_atomic_sync, run_dir / "manifest.json", manifest)


def _safe_error_message(exc: Exception) -> str:
    """Redact provider credentials from an exception before persisting it."""
    message = str(exc)
    api_key = settings.GEMINI_API_KEY
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    return re.sub(r"([?&]key=)[^&\s'\"]+", r"\1[REDACTED]", message, flags=re.IGNORECASE)


def _render_review(
    manifest: dict[str, Any],
    scripts_by_case: dict[str, list[dict[str, Any]]],
) -> str:
    """Render generated transcripts and intentionally blank human-review fields."""
    parts = [
        "# CEFR × Genre Script Review",
        "",
        f"Generated: {manifest['created_at']}",
        f"Model: `{manifest['model']}`",
        "",
        "This document packages validated model output for human review. It does not assign a CEFR score or verdict.",
        "",
    ]

    for case in manifest["cases"]:
        if case["status"] != "success":
            continue
        config = case["config"]
        speakers_by_id = {speaker["id"]: speaker["name"] for speaker in config["speakers"]}
        parts.extend(
            [
                f"## {config['cefr_level']} — {config['genre']}",
                "",
                f"- Topic: {config['topic']}",
                f"- Accent: {config['accent']}",
                f"- Duration target: {config['duration_minutes']} minutes",
                f"- Case ID: `{case['case_id']}`",
                "",
                "### Transcript",
                "",
            ]
        )
        for line in scripts_by_case[case["case_id"]]:
            speaker_name = speakers_by_id.get(line["speaker_id"], line["speaker_id"])
            parts.append(f"**{speaker_name}:** {line['text']}")
            parts.append("")

        parts.extend(["### Language notes emitted with the script", ""])
        for index, line in enumerate(scripts_by_case[case["case_id"]], start=1):
            notes = line.get("language_notes") or {}
            collocations = ", ".join(notes.get("collocations") or []) or "—"
            idioms = ", ".join(notes.get("idioms") or []) or "—"
            grammar = notes.get("grammar_point") or "—"
            parts.append(
                f"- Line {index}: collocations: {collocations}; idioms: {idioms}; grammar: {grammar}"
            )
        parts.extend(
            [
                "",
                "### Human review (leave blank until reviewed)",
                "",
                "- Vocabulary appropriateness:",
                "- Grammar appropriateness:",
                "- Collocation accuracy:",
                "- Naturalness:",
                "- Topic relevance:",
                "- Speaker balance:",
                "- Issues / recommended prompt changes:",
                "- Reviewer:",
                "- Review date:",
                "",
            ]
        )

    failed_cases = [case for case in manifest["cases"] if case["status"] == "error"]
    if failed_cases:
        parts.extend(["## Generation failures", ""])
        for case in failed_cases:
            parts.append(
                f"- `{case['case_id']}` — {case['error']['type']}: {case['error']['message']}"
            )
        parts.append("")

    return "\n".join(parts)


async def generate_samples(
    cases: list[dict[str, Any]],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    generate_function: GenerateFunction | None = None,
    sleep_function: SleepFunction | None = None,
    clock_function: ClockFunction | None = None,
    run_id: str | None = None,
) -> tuple[Path, dict[str, Any], int]:
    """Generate cases sequentially, checkpoint artifacts, and return a truthful exit code."""
    generator = generate_function or script_service.generate_script
    sleeper = sleep_function or asyncio.sleep
    clock = clock_function or time.monotonic
    run_dir = await asyncio.to_thread(_make_run_directory_sync, output_root, run_id)
    manifest = _new_manifest(cases)
    scripts_by_case: dict[str, list[dict[str, Any]]] = {}
    await _write_manifest(run_dir, manifest)

    last_request_started: float | None = None
    total = len(cases)
    for index, case in enumerate(cases, start=1):
        if last_request_started is not None:
            remaining = REQUEST_INTERVAL_SECONDS - (clock() - last_request_started)
            if remaining > 0:
                await sleeper(remaining)
        last_request_started = clock()

        print(f"[{index}/{total}] {case['case_id']} — requesting Gemini...", flush=True)
        try:
            generated_lines = await generator(case["project_id"], case["config"])
            lines = [line.model_dump(mode="json") for line in generated_lines]
            relative_output = Path("samples") / f"{case['case_id']}.json"
            await asyncio.to_thread(
                _write_json_atomic_sync,
                run_dir / relative_output,
                {"project_id": case["project_id"], "config": case["config"], "lines": lines},
            )
            scripts_by_case[case["case_id"]] = lines
            case.update(
                {
                    "status": "success",
                    "output_file": relative_output.as_posix(),
                    "line_count": len(lines),
                    "error": None,
                }
            )
            manifest["successful_cases"] += 1
            print(f"[{index}/{total}] {case['case_id']} — success ({len(lines)} lines)", flush=True)
        except Exception as exc:  # Continue the campaign while preserving the concrete failure.
            case.update(
                {
                    "status": "error",
                    "output_file": None,
                    "line_count": None,
                    "error": {"type": type(exc).__name__, "message": _safe_error_message(exc)},
                }
            )
            manifest["failed_cases"] += 1
            print(
                f"[{index}/{total}] {case['case_id']} — error: "
                f"{case['error']['type']}: {case['error']['message']}",
                file=sys.stderr,
                flush=True,
            )

        await _write_manifest(run_dir, manifest)
        review = _render_review(manifest, scripts_by_case)
        await asyncio.to_thread(_write_text_atomic_sync, run_dir / "review.md", review)

    manifest["status"] = "complete" if manifest["failed_cases"] == 0 else "completed_with_errors"
    await _write_manifest(run_dir, manifest)
    print(f"Output: {run_dir}")
    print(
        f"Summary: {manifest['successful_cases']}/{manifest['case_count']} succeeded, "
        f"{manifest['failed_cases']} failed"
    )
    return run_dir, manifest, 0 if manifest["failed_cases"] == 0 else 1


def _print_dry_run(cases: list[dict[str, Any]]) -> None:
    """Print the matrix without creating artifacts or contacting Gemini."""
    print(f"Dry run: {len(cases)} cases; no Gemini calls; no files created.")
    for index, case in enumerate(cases, start=1):
        config = case["config"]
        print(
            f"{index:02d}. {case['case_id']} | topic={config['topic']} | "
            f"accent={config['accent']} | duration={config['duration_minutes']} | "
            f"speakers={config['num_speakers']}"
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate CEFR × genre script samples for manual quality review."
    )
    parser.add_argument("--levels", nargs="+", choices=CEFR_LEVELS, default=list(CEFR_LEVELS))
    parser.add_argument(
        "--genres", nargs="+", choices=APPROVED_GENRES, default=list(APPROVED_GENRES)
    )
    parser.add_argument(
        "--duration-minutes", type=_positive_float, default=DEFAULT_DURATION_MINUTES
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        _reject_duplicates(args.levels, "CEFR level")
        _reject_duplicates(args.genres, "genre")
    except ValueError as exc:
        parser.error(str(exc))
    return args


async def run_cli(
    args: argparse.Namespace,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    generate_function: GenerateFunction | None = None,
    sleep_function: SleepFunction | None = None,
    clock_function: ClockFunction | None = None,
    run_id: str | None = None,
) -> int:
    """Execute a parsed CLI request, with injectable boundaries for isolated tests."""
    cases = build_cases(args.levels, args.genres, args.duration_minutes)
    if args.dry_run:
        _print_dry_run(cases)
        return 0
    _, _, exit_code = await generate_samples(
        cases,
        output_root,
        generate_function=generate_function,
        sleep_function=sleep_function,
        clock_function=clock_function,
        run_id=run_id,
    )
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    """Run the asynchronous campaign from a synchronous command-line entry point."""
    return asyncio.run(run_cli(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
