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
from contextlib import contextmanager
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


@contextmanager
def _runner_module_with_argv(extra_argv):
    """Task 18.4: same snapshot/restore pattern as `runner_module` above, but with
    caller-supplied argv (e.g. `--matrix cloud_first`) instead of the bare stripped
    argv the shared fixture always uses -- needed to exercise the module's
    argv-before-import env-setting logic for a specific `--matrix` value."""
    env_snapshot = dict(os.environ)
    argv_snapshot = list(sys.argv)
    module_name = "run_ai_operational_trial_under_test_argv"
    try:
        sys.argv = [argv_snapshot[0], *extra_argv]
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


# --- Task 18.4: --matrix cloud_first ------------------------------------------------


def test_matrix_cloud_first_sets_ai_mode_and_allow_cloud_env_vars():
    pre_ai_mode = os.environ.get("DIE_AI_MODE")
    pre_allow_cloud = os.environ.get("DIE_AI_ALLOW_CLOUD")

    with _runner_module_with_argv(["--matrix", "cloud_first"]):
        assert os.environ["DIE_AI_MODE"] == "cloud_first"
        assert os.environ["DIE_AI_ALLOW_CLOUD"] == "true"

    # PM review C2: must not leak into the rest of the pytest session --
    # tests/conftest.py's N1 fix (_neutralize_cloud_config) depends on
    # AI_ALLOW_CLOUD=False holding for the whole session.
    assert os.environ.get("DIE_AI_MODE") == pre_ai_mode
    assert os.environ.get("DIE_AI_ALLOW_CLOUD") == pre_allow_cloud


def test_matrix_local_does_not_set_allow_cloud_env_var():
    with _runner_module_with_argv(["--matrix", "local"]):
        assert os.environ["DIE_AI_MODE"] == "local"
        assert "DIE_AI_ALLOW_CLOUD" not in os.environ


# --- Task 18.4: compute_matrix_aggregates fallback-rate fields (D22, informational) --


def _run(job_status="complete", fallback_used=False, fallback_count=0, calls=None):
    return {
        "job_status": job_status,
        "content": None,
        "failure_class": None,
        "error_code": None,
        "sections": [],
        "repair_count": 0,
        "fallback_count": fallback_count,
        "fallback_used": fallback_used,
        "call_stats": {"total_backoff_seconds": 0.0, "max_attempts_on_one_call": 0},
        "metrics": {"calls": calls or []},
    }


def test_compute_matrix_aggregates_fallback_rate_none_when_no_calls(runner_module):
    aggregates = runner_module.compute_matrix_aggregates([_run()])
    assert aggregates["call_fallback_rate"] is None
    assert aggregates["job_fallback_rate"] == 0.0
    assert aggregates["fallback_reason_counts"] == {}


def test_compute_matrix_aggregates_fallback_rate_mixed_reasons(runner_module):
    calls_job1 = [
        {"fallback_used": False},
        {"fallback_used": True, "fallback_reason": "ProviderRateLimitError"},
    ]
    calls_job2 = [{"fallback_used": True, "fallback_reason": "ProviderTimeoutError"}]
    calls_job3 = [{"fallback_used": False}]
    runs = [
        _run(fallback_used=True, fallback_count=1, calls=calls_job1),
        _run(fallback_used=True, fallback_count=1, calls=calls_job2),
        _run(fallback_used=False, calls=calls_job3),
    ]

    aggregates = runner_module.compute_matrix_aggregates(runs)

    assert aggregates["call_fallback_rate"] == round(2 / 4, 4)
    assert aggregates["job_fallback_rate"] == round(2 / 3, 4)
    assert aggregates["fallback_reason_counts"] == {"ProviderRateLimitError": 1, "ProviderTimeoutError": 1}
