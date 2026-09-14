"""Tests for the Task 2.1a CEFR × genre sample-export CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.exceptions import ScriptGenerationError
from app.services.script_service import LanguageNotesOut, ScriptLineOut
from scripts import generate_cefr_review_samples as sample_cli


def _line_for(config: dict, text: str = "A generated line.") -> ScriptLineOut:
    """Build a validated fake line using a speaker UUID from the supplied case."""
    return ScriptLineOut(
        id="line_001",
        speaker_id=config["speakers"][0]["id"],
        text=text,
        language_notes=LanguageNotesOut(
            collocations=["generated line"], idioms=[], grammar_point="Present Simple"
        ),
    )


def test_default_matrix_has_exact_order_casing_topics_and_unique_ids() -> None:
    cases = sample_cli.build_cases(
        sample_cli.CEFR_LEVELS,
        sample_cli.APPROVED_GENRES,
        sample_cli.DEFAULT_DURATION_MINUTES,
    )

    assert len(cases) == 18
    assert [case["case_id"] for case in cases[:6]] == [
        "A1__small_talk",
        "A1__interview",
        "A1__news",
        "A2__small_talk",
        "A2__interview",
        "A2__news",
    ]
    assert [case["case_id"] for case in cases[-3:]] == [
        "C2__small_talk",
        "C2__interview",
        "C2__news",
    ]
    assert len({case["case_id"] for case in cases}) == 18
    assert len({case["project_id"] for case in cases}) == 18

    speaker_ids = [speaker["id"] for case in cases for speaker in case["config"]["speakers"]]
    assert len(speaker_ids) == len(set(speaker_ids)) == 36
    for case in cases:
        config = case["config"]
        assert config["cefr_level"] in ("A1", "A2", "B1", "B2", "C1", "C2")
        assert config["topic"] == sample_cli.TOPICS_BY_GENRE[config["genre"]]
        assert config["accent"] == "american"
        assert config["duration_minutes"] == 2.0
        assert config["num_speakers"] == 2


def test_parse_args_supports_subsets_and_rejects_invalid_duration_or_duplicates() -> None:
    args = sample_cli.parse_args(
        ["--levels", "A1", "C2", "--genres", "news", "--duration-minutes", "0.5"]
    )
    assert args.levels == ["A1", "C2"]
    assert args.genres == ["news"]
    assert args.duration_minutes == 0.5

    with pytest.raises(SystemExit):
        sample_cli.parse_args(["--duration-minutes", "0"])
    with pytest.raises(SystemExit):
        sample_cli.parse_args(["--levels", "a1"])
    with pytest.raises(SystemExit):
        sample_cli.parse_args(["--levels", "A1", "A1"])


async def test_dry_run_makes_no_call_and_creates_no_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    async def forbidden_generator(project_id: str, config: dict) -> list[ScriptLineOut]:
        raise AssertionError("dry-run must not call Gemini")

    args = sample_cli.parse_args(["--levels", "A1", "--genres", "small_talk", "--dry-run"])
    output_root = tmp_path / "must-not-exist"

    exit_code = await sample_cli.run_cli(
        args, output_root=output_root, generate_function=forbidden_generator
    )

    assert exit_code == 0
    assert not output_root.exists()
    output = capsys.readouterr().out
    assert "Dry run: 1 cases; no Gemini calls; no files created." in output
    assert "Planning a healthy weekday routine" in output


async def test_success_writes_complete_traceability_and_human_review(tmp_path: Path) -> None:
    received: list[tuple[str, dict]] = []

    async def fake_generator(project_id: str, config: dict) -> list[ScriptLineOut]:
        received.append((project_id, config))
        return [_line_for(config, text=f"Sample for {config['cefr_level']} {config['genre']}.")]

    cases = sample_cli.build_cases(["A1"], ["small_talk"], 2.0)
    run_dir, manifest, exit_code = await sample_cli.generate_samples(
        cases,
        tmp_path,
        generate_function=fake_generator,
        run_id="successful-run",
    )

    assert exit_code == 0
    assert manifest["status"] == "complete"
    assert manifest["successful_cases"] == 1
    assert manifest["failed_cases"] == 0
    assert received == [(cases[0]["project_id"], cases[0]["config"])]

    stored_manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    stored_case = stored_manifest["cases"][0]
    config = stored_case["config"]
    assert {
        "topic",
        "cefr_level",
        "genre",
        "accent",
        "duration_minutes",
        "num_speakers",
        "language_features",
        "speakers",
    } <= config.keys()
    assert stored_case["project_id"] == cases[0]["project_id"]
    assert stored_case["status"] == "success"
    assert stored_case["output_file"] == "samples/A1__small_talk.json"
    assert stored_case["line_count"] == 1

    sample = json.loads((run_dir / stored_case["output_file"]).read_text(encoding="utf-8"))
    assert sample["config"] == config
    assert sample["lines"][0]["text"] == "Sample for A1 small_talk."

    review = (run_dir / "review.md").read_text(encoding="utf-8")
    assert "**Alex:** Sample for A1 small_talk." in review
    assert "### Human review (leave blank until reviewed)" in review
    assert "- Vocabulary appropriateness:\n" in review
    assert "- Issues / recommended prompt changes:\n" in review
    assert "does not assign a CEFR score or verdict" in review


async def test_failure_preserves_success_records_error_redacts_key_and_exits_nonzero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_count = 0
    secret = "secret-key-for-redaction"
    monkeypatch.setattr(sample_cli.settings, "GEMINI_API_KEY", secret)

    async def fake_generator(project_id: str, config: dict) -> list[ScriptLineOut]:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ScriptGenerationError(
                f"request failed: https://provider.invalid?key={secret}&case=2"
            )
        return [_line_for(config, text="Preserved successful sample.")]

    async def no_sleep(seconds: float) -> None:
        return None

    cases = sample_cli.build_cases(["A1"], ["small_talk", "interview"], 2.0)
    run_dir, manifest, exit_code = await sample_cli.generate_samples(
        cases,
        tmp_path,
        generate_function=fake_generator,
        sleep_function=no_sleep,
        run_id="partial-run",
    )

    assert exit_code == 1
    assert manifest["status"] == "completed_with_errors"
    assert manifest["successful_cases"] == 1
    assert manifest["failed_cases"] == 1
    assert (run_dir / "samples" / "A1__small_talk.json").is_file()
    assert not (run_dir / "samples" / "A1__interview.json").exists()

    stored = (run_dir / "manifest.json").read_text(encoding="utf-8")
    assert secret not in stored
    stored_manifest = json.loads(stored)
    failed = stored_manifest["cases"][1]
    assert failed["status"] == "error"
    assert failed["error"] == {
        "type": "ScriptGenerationError",
        "message": "request failed: https://provider.invalid?key=[REDACTED]&case=2",
    }
    review = (run_dir / "review.md").read_text(encoding="utf-8")
    assert "Preserved successful sample." in review
    assert "## Generation failures" in review
    assert secret not in review


async def test_request_starts_are_throttled_by_the_declared_rate_limit(
    tmp_path: Path,
) -> None:
    now = 100.0
    starts: list[float] = []
    sleeps: list[float] = []

    def fake_clock() -> float:
        return now

    async def fake_sleep(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    async def fake_generator(project_id: str, config: dict) -> list[ScriptLineOut]:
        starts.append(now)
        return [_line_for(config)]

    cases = sample_cli.build_cases(["A1"], list(sample_cli.APPROVED_GENRES), 2.0)
    _, _, exit_code = await sample_cli.generate_samples(
        cases,
        tmp_path,
        generate_function=fake_generator,
        sleep_function=fake_sleep,
        clock_function=fake_clock,
        run_id="throttle-run",
    )

    assert exit_code == 0
    assert sleeps == pytest.approx(
        [sample_cli.REQUEST_INTERVAL_SECONDS, sample_cli.REQUEST_INTERVAL_SECONDS]
    )
    assert starts[1] - starts[0] == pytest.approx(sample_cli.REQUEST_INTERVAL_SECONDS)
    assert starts[2] - starts[1] == pytest.approx(sample_cli.REQUEST_INTERVAL_SECONDS)
