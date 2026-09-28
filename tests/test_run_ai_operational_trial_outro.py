"""Tests for scripts/run_ai_operational_trial.py's ENH-014 outro-heuristic widening +
`has_outro_last3` gate wiring.

Real evidence, verified per-case rather than trusted from paraphrase (design doc
D19.ENH14-a..c, .viepilot/phases/19-remotion/tasks/task-enh-014.md):

- Gate B-7 run 4 and Gate B-8 run 5: already covered by
  tests/test_run_ai_operational_trial.py / this file's negative test respectively, both
  fixed by the `has_outro_last3` switch alone via *existing* markers ("take care",
  "thank you for") -- no new marker is required for either.
- Gate B-11 run 1 is the one case that genuinely needs new markers: its real evidence JSON
  (data/quality_reviews/phase15/gate-b11/gate-b11-20260926T042435Z.json) records both
  `has_outro` and `has_outro_last3` as False. Its real project no longer exists in any
  locally-present DB (a cloud-first run with no retained `trial-data/` snapshot -- checked
  `data/app.db` read-only, not found), so its test text is the exact quote from
  `docs/operations/phase18-gate-b11.md` §2 (PM-verified, owner-accepted D31 at the time --
  the report itself is the authoritative source, not a paraphrase of it). The line boundary
  at the report's own "…" is a disclosed inference, not fabricated content: everything on
  either side of it is the report's real, verbatim quoted text.
- Gate B-11 run 2's real evidence already shows `has_outro_last3=True`, confirming the same
  report quote's line-boundary inference is consistent with the real recorded flags.
- Gate B-8 run 5's real last-3-lines text (including the negative-test line) was fetched
  directly, read-only, from its own `trial-data/app.db` -- a throwaway trial DB the runner
  itself wrote, not the real `data/app.db` (no write-restriction applies to reading it).
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Same importlib-based load + os.environ/sys.argv snapshot-restore pattern as
# tests/test_run_ai_operational_trial.py's own `runner_module` fixture (see that file's
# module docstring for why a bare top-level import would leak env-var writes into every
# test collected afterwards) -- duplicated here rather than cross-imported, matching this
# project's existing convention of each test file owning its own fixtures verbatim (e.g.
# every *_browser.py test file duplicates its own `_envelope()` rather than importing one).
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_ai_operational_trial.py"


@pytest.fixture
def runner_module():
    env_snapshot = dict(os.environ)
    argv_snapshot = list(sys.argv)
    module_name = "run_ai_operational_trial_outro_under_test"
    try:
        sys.argv = [argv_snapshot[0]]
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

# --- Gate B-11 run 1: docs/operations/phase18-gate-b11.md §2, PM-verified real quote -----
# Real evidence JSON confirms both has_outro=False and has_outro_last3=False for this run --
# the only one of the 4 known false negatives that genuinely needs new markers.
_B11_RUN1_LINE_2ND_LAST = "We truly appreciate you tuning in to explore these health concepts with us."
_B11_RUN1_LINE_LAST = "We look forward to seeing you in our next session at Daily Intel English Studio."

# --- Gate B-11 run 2: same report, same section -- real evidence confirms has_outro_last3=True
_B11_RUN2_LINE_2ND_LAST = (
    "Thank you for being part of our community and for joining us on this enlightening episode."
)
_B11_RUN2_LINE_LAST = "we eagerly anticipate welcoming you back here for another session next week."

# --- Gate B-8 run 5: real text, fetched read-only from
# data/quality_reviews/phase15/gate-b8/trial-data/app.db, project
# d1a76e4e-8d2a-49a5-ab25-3aecb49ac932, line_index 41-43. Already fixed by has_outro_last3
# + the *existing* "thank you for" marker -- no new marker required for this case.
_B8_RUN5_LAST_3_LINES = [
    "That sounds like a great idea for all of us to start right now and see the "
    "difference in just a few weeks.",
    "Thank you for listening to Daily Intel English Studio. We hope your new journey "
    "starts today and brings positive change to your life.",
    "Remember that every tiny effort adds up, so keep going and enjoy the path to "
    "better health ahead of you.",
]


@pytest.mark.parametrize(
    "last3_lines,expect_has_outro,label",
    [
        pytest.param(
            [_B11_RUN1_LINE_2ND_LAST, _B11_RUN1_LINE_2ND_LAST, _B11_RUN1_LINE_LAST],
            True,
            "gate-b11-run1",
            id="b11-run1-needs-new-markers",
        ),
        pytest.param(
            [_B11_RUN2_LINE_2ND_LAST, _B11_RUN2_LINE_2ND_LAST, _B11_RUN2_LINE_LAST],
            True,
            "gate-b11-run2",
            id="b11-run2-existing-plus-new-markers",
        ),
        pytest.param(
            _B8_RUN5_LAST_3_LINES,
            False,
            "gate-b8-run5",
            id="b8-run5-existing-marker-only",
        ),
    ],
)
def test_widened_markers_catch_every_real_ending(runner_module, last3_lines, expect_has_outro, label):
    """`expect_has_outro` is the single-last-line result under the *widened* markers (not a
    reproduction of each run's original recorded value) -- False for Gate B-8 run 5 because
    its true last line has no sign-off marker at all (only the 2nd-to-last line does, which
    is exactly why the has_outro_last3 switch is the fix for that case); True for both Gate
    B-11 runs because their true last lines now match the new markers directly."""
    texts_lower = [text.lower() for text in last3_lines]

    assert runner_module._has_outro(texts_lower[-1], None) is expect_has_outro, label
    assert runner_module._has_outro_in_last_n(texts_lower, 3, None) is True, label


def test_b11_run1_last_line_alone_needs_the_new_markers(runner_module):
    """The specific, narrower claim design doc D19.ENH14-a makes: Gate B-11 run 1's real
    evidence has *both* has_outro and has_outro_last3 False today -- confirm the true last
    line alone (not aided by the 2nd-to-last line) now matches via the new markers
    ("look forward", "next session"), not just via last-3-lines position."""
    assert runner_module._has_outro(_B11_RUN1_LINE_LAST.lower(), None) is True


def test_negative_case_real_midscript_dialogue_does_not_overfire(runner_module):
    """D19.ENH14-c: a real, non-ending B1 line (Gate B-8 run 5, line_index 41 -- fetched
    read-only from the same trial-data/app.db) must not trigger the widened heuristic,
    proving the new markers don't overfire on ordinary small-talk content."""
    midscript_line = (
        "That sounds like a great idea for all of us to start right now and see the "
        "difference in just a few weeks."
    ).lower()

    assert runner_module._has_outro(midscript_line, None) is False
    assert runner_module._has_outro_in_last_n([midscript_line], 1, None) is False


def _run(*, job_status="complete", has_outro_last3):
    return {
        "job_status": job_status,
        "content": {"has_outro_last3": has_outro_last3, "all_checks_pass": True, "total_words": 800},
        "failure_class": None,
        "error_code": None,
        "sections": [],
        "repair_count": 0,
        "fallback_count": 0,
        "fallback_used": False,
        "call_stats": {"total_backoff_seconds": 0.0, "max_attempts_on_one_call": 0},
        "metrics": {"calls": []},
    }


def test_compute_matrix_aggregates_adds_outro_present_last3_rate(runner_module):
    """D19.ENH14-b: a new aggregate field, not a rename -- `compute_matrix_aggregates` had
    no outro-related field at all before this task."""
    runs = [
        _run(has_outro_last3=True),
        _run(has_outro_last3=True),
        _run(has_outro_last3=False),
    ]

    aggregates = runner_module.compute_matrix_aggregates(runs)

    assert aggregates["outro_present_last3_rate"] == round(2 / 3, 4)


def test_compute_matrix_aggregates_outro_rate_none_when_no_completed_runs(runner_module):
    aggregates = runner_module.compute_matrix_aggregates([_run(job_status="error", has_outro_last3=False)])

    assert aggregates["outro_present_last3_rate"] is None
