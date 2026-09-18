"""Verify Phase 13's pre-implementation AI fixtures and legacy API contract.

This is deliberately offline: it validates the frozen inputs and representative
outputs without calling a model, opening the application database, or printing secrets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.learning import LearningPackOut  # noqa: E402
from app.models.project import ScriptConfig  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "ai"


def _load_json(name: str) -> dict[str, Any]:
    """Load one required UTF-8 JSON fixture."""
    path = FIXTURE_DIR / name
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must contain one JSON object")
    return value


def _verify_projects(payload: dict[str, Any]) -> int:
    """Validate the three pinned CEFR project inputs with production models."""
    projects = payload.get("projects")
    if not isinstance(projects, list) or len(projects) != 3:
        raise ValueError("golden_projects.json must contain exactly three projects")
    levels: set[str] = set()
    for raw in projects:
        if not isinstance(raw, dict):
            raise ValueError("each golden project must be an object")
        fixture_id = raw.get("fixture_id")
        config = {key: value for key, value in raw.items() if key != "fixture_id"}
        validated = ScriptConfig.model_validate(config)
        if not isinstance(fixture_id, str) or not fixture_id:
            raise ValueError("each golden project needs a fixture_id")
        levels.add(validated.cefr_level)
    if levels != {"A2", "B1", "C1"}:
        raise ValueError(f"expected A2/B1/C1 fixtures, got {sorted(levels)}")
    return len(projects)


def _verify_contracts(payload: dict[str, Any]) -> int:
    """Validate frozen legacy envelopes and representative generated content."""
    envelope = payload.get("response_envelope")
    endpoints = payload.get("endpoints")
    script = payload.get("representative_script")
    pack = payload.get("representative_learning_pack")
    if not isinstance(envelope, dict) or envelope.get("required_keys") != [
        "success",
        "data",
        "error",
        "meta",
    ]:
        raise ValueError("legacy response envelope drifted")
    if not isinstance(endpoints, dict) or len(endpoints) != 4:
        raise ValueError("expected four frozen legacy endpoint contracts")
    if not isinstance(script, list) or not script:
        raise ValueError("representative script must be a non-empty array")
    required_line_keys = {"id", "speaker_id", "text", "language_notes"}
    for line in script:
        if not isinstance(line, dict) or set(line) != required_line_keys:
            raise ValueError("representative script line shape drifted")
        if not str(line["text"]).strip():
            raise ValueError("representative script contains blank text")
    LearningPackOut.model_validate(pack)
    return len(endpoints)


def main() -> int:
    """Run every offline baseline check and print only non-sensitive counts."""
    project_count = _verify_projects(_load_json("golden_projects.json"))
    endpoint_count = _verify_contracts(_load_json("legacy_contracts.json"))
    print(f"AI baseline OK: {project_count} golden projects, {endpoint_count} endpoint contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
