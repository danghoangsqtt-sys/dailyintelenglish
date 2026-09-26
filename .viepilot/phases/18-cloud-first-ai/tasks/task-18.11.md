# Task 18.11 — Flip `AI_MODE` default to `cloud_first` (D31, close-out)

- **Status:** done
- **Owner:** Coder
- **Priority:** P0 (small; card + code + tests in one commit, per the PM's instruction — the
  design is fixed by plan Amendment C's close-out step and Gate B-11's PASS, nothing to review
  first)
- **Dependency:** Gate B-11 PASS, owner-accepted (D31); `docs/operations/phase18-gate-b11.md`
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §5 "Version", plan
  Amendment C's close-out condition ("Only on a PASS does the `AI_MODE` default flip to
  `cloud_first`")

## What changed

1. `app/core/config.py`: `AI_MODE: str = "local"` → `"cloud_first"`. Comments updated — the old
   "AI_MODE still defaults to local... until B-9/B-10/B-11" language (now stale, since B-11
   passed) replaced with the close-out rationale and an explicit restatement that invariant
   32/D24's `compute_effective_mode` collapse still fully protects a no-key install regardless of
   this default.
2. `.env.example`: `DIE_AI_MODE=local` → `cloud_first`, comment updated to match.
3. Swept every test asserting a literal `"local"` near `AI_MODE`/`ai_mode` — both apparent hits
   (`tests/test_run_ai_operational_trial.py:131`'s `--matrix local` runner-argv test,
   `tests/test_settings_service.py:501`'s `load_ai_mode_from_db` restore-a-stored-value test) turned
   out to be testing something else entirely (an explicit test value/an independent runner-script
   default), not the `Settings` class default -- confirmed by the full suite passing unchanged
   before any test edits were needed here.
4. New tests (`tests/test_ai_router.py`): `test_default_ai_mode_is_cloud_first` (reads
   `Settings.model_fields["AI_MODE"].default` -- pure metadata, deliberately never constructs a
   real `Settings()`, since that would re-read the real `.env` file and could pull the owner's
   real keys into the test process, the exact class of risk N1/N2 closed) and
   `test_ai_mode_default_still_collapses_to_local_with_no_provider_configured` (calls
   `compute_effective_mode` directly with explicit args, same secret-safety reasoning).
5. `CHANGELOG.md`: closed `[Unreleased]` into `## [1.1.0-beta] - 2026-09-26` (plan §5's
   `1.0.0-beta` → `1.1.0-beta` bump), with a new empty `[Unreleased]` above it. The 1.1.0-beta
   section covers everything accumulated since 1.0.0-beta (Phases 16, 17, 18 — already-written
   entries, unchanged), plus this task's own entry describing the default flip.

## Verification

Full suite, `ruff`, real DB untouched. No revert-and-confirm-failure needed -- this task is a
default-value flip plus new tests that assert the new value directly (there's no prior "wrong"
behavior to revert into; the two "candidate" pre-existing tests were confirmed unaffected by
running the untouched suite first).

## Evidence

- Full suite: **1175 passed** (1173 baseline + 2 new). `ruff check .` -> all checks passed. Real
  DB untouched throughout (the conftest guard never tripped).
- No test needed changing -- the two literal-`"local"` hits swept for were both testing something
  independent of the `Settings` class default (confirmed by running the full suite unchanged
  before touching any test file).
- One full-suite run hit 2 one-off failures (`test_script_api.py::test_concurrent_script_saves_
  do_not_interleave`, a DB write-concurrency timing test; `test_script_jobs_browser.py::test_
  generate_disabled_with_guidance_when_ollama_missing`, a browser test gated entirely on mocked
  `/api/ai/health` data, unrelated to `AI_MODE`'s real default) -- both passed immediately in
  isolation, and a full clean re-run (1175/1175) confirmed neither is a regression from this
  task. Matches this project's own previously-documented pattern of a rare timing-sensitive flake
  under a long, loaded full-suite run (see `.viepilot/HANDOFF.json`'s Phase 3 close-out note).
