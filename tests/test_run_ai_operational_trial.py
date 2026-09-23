"""Tests for scripts/run_ai_operational_trial.py's `has_outro_last3` diagnostic
(Task 17.2, ENH-010).

PM review C2: this script does real work at *module import time* -- it reads
sys.argv for --gate/--matrix/--mode and unconditionally sets
os.environ["DIE_AI_MODE"]/["DIE_DATA_DIR"] before importing app.main (see the
script's own module docstring). This file's `runner_module` fixture snapshots
and restores os.environ, sys.argv, and sys.modules around a fresh
`importlib`-based load of the script (following the same pattern already used
by tests/test_check_dependencies.py for scripts/check_dependencies.py), so
this test file's collection order relative to the rest of the suite -- and
the rest of the suite's order relative to this file -- can never matter. A
bare top-level `import scripts.run_ai_operational_trial` would instead leak
those env-var writes into every test collected afterwards.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_ai_operational_trial.py"


@pytest.fixture
def runner_module():
    env_snapshot = dict(os.environ)
    argv_snapshot = list(sys.argv)
    module_name = "run_ai_operational_trial_under_test"
    try:
        sys.argv = [argv_snapshot[0]]  # strip pytest's own args -- no --gate/--matrix/--mode
        spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(module_name, None)
        os.environ.clear()
        os.environ.update(env_snapshot)
        sys.argv = argv_snapshot


# Verbatim from the real Gate B-7 run 4 ending (read-only trial DB investigation,
# project 976be88b-eb93-444f-b2f8-664d9e7a0383 -- see task-17.2.md), the exact case
# this diagnostic exists to fix: the sign-off sits 2nd-to-last, not last.
_RUN4_LAST_3_LINES = [
    "Thank you so much for joining us on this final last section of our show about "
    "healthy living and daily wellness tips.",
    "It was a genuine pleasure talking to you both. Please remember always to take "
    "care of yourself today and throughout the rest of your week.",
    "Until then, try adopting one small new habit. Your future health and happiness "
    "depends entirely on the choices you make right now.",
]


def test_has_outro_in_last_n_catches_the_gate_b7_run4_false_negative(runner_module):
    texts_lower = [text.lower() for text in _RUN4_LAST_3_LINES]

    assert runner_module._has_outro(texts_lower[-1], None) is False
    assert runner_module._has_outro_in_last_n(texts_lower, 3, None) is True


def test_analyze_script_gate_decision_still_uses_has_outro_only(runner_module):
    """Required behaviour #2: `has_outro_last3` is recorded next to `has_outro`, but
    `checks`/`all_checks_pass`/`outro_present` keep reading from `has_outro` alone --
    this run's own has_outro is False even though has_outro_last3 is True, so if
    outro_present ever flipped to True the gate decision would have silently started
    trusting the new field instead."""
    lines = [
        {"speaker_id": "S1", "text": _RUN4_LAST_3_LINES[0]},
        {"speaker_id": "S2", "text": _RUN4_LAST_3_LINES[1]},
        {"speaker_id": "S1", "text": _RUN4_LAST_3_LINES[2]},
    ]
    known_speaker_ids = {"S1", "S2"}

    result = runner_module.analyze_script(lines, known_speaker_ids, outline_last_objective=None)

    assert result["has_outro"] is False
    assert result["has_outro_last3"] is True
    assert result["checks"]["outro_present"] is False
    assert result["all_checks_pass"] is False
