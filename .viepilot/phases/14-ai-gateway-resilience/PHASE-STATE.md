# Phase 14 State — AI Gateway Resilience and Section Budget Rebalancing

## Metadata

- **Phase:** 14
- **Slug:** `14-ai-gateway-resilience`
- **Status:** in_progress
- **Started:** 2026-09-21
- **Closed:** —
- **Controlling plan:** `docs/implementation/phase-14-ai-gateway-resilience.md`
- **Source brainstorm:** `docs/brainstorm/session-2026-09-21.md`
- **Authorization:** user opened Phase 14 after the PM/Tester's independent Gate B
  post-mortem; execution runs as two parallel sessions (PM: Claude Opus 5; Coder:
  Claude Sonnet 5) under the file partition in plan §10.
- **Ownership of this folder:** PM until the handover commit that adds this file; Coder
  afterwards. The PM then reads only and requests edits.

## Preflight

- Branch `main`; upstream `origin/main`; worktree clean at HEAD `3b8d328` when the PM
  started; Phase 13 Tasks 13.0–13.9 done and pushed; Task 13.10 **blocked** (D1).
- Full suite baseline: **808/808 pass**, `ruff` clean.
- Dev server on port 8000 is running and must never be stopped by either session.
- Ollama 0.34.2, `qwen3.5:9b` digest `6488c96fa5fa…`, requires the full env set
  (`OLLAMA_HOST`, `OLLAMA_MODELS=D:\DataAdmin\OllamaModels`, `OLLAMA_MAX_LOADED_MODELS=1`,
  `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_QUEUE=4`, `OLLAMA_NO_CLOUD=1`) before `serve`.
- Gemini `gemini-3.8-flash` live-verified stable; transient 503 observed
  (`200 → 503 → 200`); account quota recorded in constants as 5 RPM / 20 RPD
  (2026-09-14) — must be re-read live before 14.4b.
- PM re-verified from the Phase 13 trial DB on 2026-09-21: 18 accepted sections, mean
  145.9 words, σ 19.5; every job row has `repair_count=0`, `fallback_used=0`,
  `actual_provider=NULL`, `model=NULL` (telemetry gap wider than `repair_count` alone).
- ADR-001 conflict found and resolved doc-first: Decision 3 capped infrastructure retry
  at one; amendment A1 recorded in the ADR in the handover commit.

## Task status

| Task | Description | Owner | Status | Blocking gate |
|---|---|---|---|---|
| 14.1 | Bounded exponential backoff for transient errors in `AIRouter` | Coder | done | Backoff proven to wait; deadline honoured |
| 14.2 | Job telemetry: repair/fallback/provider/attempts/error codes | Coder | done | Row fields written; `provider_*` codes |
| 14.3 | Running section budget; hard gate only at global ±10% | Coder | done | Constants pinned; carry/resume tests |
| 14.4a | Runner preparation (classification, per-section stats, aggregates) | Coder | done | Reaggregate dry run |
| 14.4b | Gate B second run, both providers, declared protocol | PM | pending | Decision rules in plan §4.4 |
| 14.5 | Correct `docs/operations/phase13-acceptance.md` | PM | pending | Original text preserved |
| 14.6 | Resume Task 13.10 with evidence-selected rollout mode | Both | pending | 14.4b decision + 14.5 |

Execution order: 14.1 → 14.2 → 14.3 → 14.4a (Coder, sequential). 14.5 runs in parallel
(PM). 14.4b starts only after 14.1–14.4a are merged and the PM has reviewed the diffs.
14.6 last.

## Decisions

- D3: backoff 1 s → 2 s → 4 s, 4 attempts, same model, inside the 120 s deadline;
  content-class errors keep one immediate retry; cascade ban unchanged.
- D4: per-section ±15% becomes repair trigger + drift signal; hard gate only at the
  global ±10%; one final-section budget repair; **no tolerance value changes**.
- D5: telemetry lands before 14.3 so repair effectiveness is measurable.
- D6: Gate B-2 measures both providers sequentially; infra vs content failures are
  separate verdicts (PASS / FAIL-CONTENT / FAIL-INFRA for Gemini).
- D7/D8: acceptance report corrected additively; `gemini-3.8-flash` kept, no previews.
- Open (decide with 14.4b data): compensate the −9% undershoot or not; 3 vs 4 attempts.

## Evidence log

- 2026-09-21: PM read the brainstorm, Phase 13 plan, ADR-001, SYSTEM-RULES, TRACKER,
  HANDOFF, the acceptance report, `router.py`, `contracts.py`, `script_pipeline.py`,
  `ai_job_service.py`, `ai_worker.py`, constants/config, and the trial runner before
  writing the plan; re-verified the checkpoint statistics from the trial DB.
- 2026-09-21: controlling plan, SPEC, PHASE-STATE, task cards 14.1–14.6, and ADR-001
  amendment A1 written. No product code modified. Handover to Coder at this commit.
- 2026-09-21: Coder implemented Task 14.1 (`app/services/ai/router.py`,
  `contracts.py`, `app/core/constants.py`; commit `2384578`), then reported a block:
  4 pre-existing tests outside the task's allowed files
  (`tests/test_learning_service.py`, `tests/test_script_service.py`,
  `tests/test_youtube_service.py`) scripted 2 transient outcomes for the old
  1-retry exhaustion policy and failed under the new 4-attempt policy. PM
  independently reproduced the 4 failures and issued Amendment A (commit
  `378bf4d`, plan §6 Task 14.1) adding those 3 files to the allowed list,
  test-only, scoped to the 4 `*_wraps_provider_error*` tests. Coder mirrored the
  amendment into task-14.1.md and applied the fix (4 scripted outcomes + patched
  `app.services.ai.router.sleep`). Full suite: **814 passed**, 0 failed (net +6
  over the 808 baseline, all in `tests/test_ai_router.py`'s own required
  verification tests -- not +4 as first estimated; see task-14.1.md "Commands and
  results" for the count reconciliation). `ruff check app tests scripts` clean.
  Task 14.1 status: done.
- 2026-09-21: Coder implemented Task 14.2 (`app/services/ai_job_service.py`
  gains `record_generation_call`/`provider_error_code`; `app/models/ai_job.py`
  gains `AIJobOut.metrics` via a `model_validator` that parses `metrics_json`
  (no `app/api/ai_jobs.py` change needed); both `script_pipeline.py` and
  `learning_pipeline.py` route every router call through a small
  `_call_router` wrapper that records telemetry in its own short
  `write_transaction` -- never spanning the actual inference call -- and map
  `ProviderError` subclasses to `provider_*` job `error_code`s instead of
  letting them fall through to `handler_exception`; script checkpoints gain
  `target_nominal`/`target_effective`/`words`/`deviation_pct`/`repaired`/
  `words_before_repair`/`errors_before_repair` in `metrics_json`,
  `target_effective == target_nominal` until Task 14.3). `fallback_reason` is
  accepted by `record_generation_call` but not populated by either pipeline in
  this task -- the router doesn't yet surface the local failure's error class
  on `GenerationResult` (out of 14.1's closed file set); flagged in
  task-14.2.md rather than silently skipped or scope-creeping into 14.1.
  Revert-and-confirm-failure on the `repair_count` increment: 3 targeted tests
  failed for the right reason with it disabled, passed once restored. Full
  suite: **848 passed**, 0 failed (net +34 over the 814 baseline after 14.1).
  `ruff check app tests scripts` clean. Task 14.2 status: done.
- 2026-09-21: PM reviewed commit `cde8e79` and found a real misclassification:
  `SchemaValidationError` is a `ProviderError` subclass but a content failure
  (raised by `parse_and_validate` after a successful router call); the script
  outline path's `except ProviderError` caught it and `provider_error_code`
  had no entry for it, so it fell through to the generic `"provider_error"`
  fallback -- which Gate B-2's classification (plan §4.4) reads as `infra`
  purely from the `provider_` prefix, misclassifying a content failure as
  infrastructure. PM issued Amendment B (commit `c93d152`) requiring
  `provider_error_code(SchemaValidationError) == "schema_validation_failed"`
  (a `content`-class code) plus one service test and one e2e pipeline test.
  Coder implemented 14.2-b: one line added to `_PROVIDER_ERROR_CODES` in
  `ai_job_service.py` (no change needed to `_call_router`/`_fail_provider`/
  either pipeline, since every call site already routes through the shared
  lookup); updated/added tests in `tests/test_ai_job_service.py` and
  `tests/test_script_pipeline.py`. Full suite: **850 passed**, 0 failed.
  `ruff check app tests scripts` clean. Task 14.2 (incl. Amendment B) status:
  done.
- 2026-09-21: Coder implemented Task 14.3 (`app/services/script_pipeline.py`,
  `app/core/constants.py`: `SCRIPT_SECTION_CARRY_CAP=0.35`,
  `SCRIPT_LAST_SECTION_CARRY_CAP=0.5`,
  `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS=1`; `SCRIPT_GLOBAL_WORD_TOLERANCE`/
  `SCRIPT_SECTION_WORD_TOLERANCE` unchanged and now pinned by a test).
  `validate_section` split into `validate_section_structure` +
  `validate_section_word_budget`; a section's one repair pass now targets its
  *effective* target (nominal adjusted by carried-forward drift, clamped);
  after repair a remaining structural error still hard-fails
  (`section_validation_failed`), but a remaining word-deviation-only error is
  now accepted and the drift carried forward -- the product's only hard
  word-count gate stays `validate_global`'s ±10% total, unchanged. One bounded
  final-section budget repair (`SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS=1`)
  fires only when the global total (not any hard error) is the problem.
  Resume recomputes `carry` from checkpoints' stored `target_effective`
  (PM-reviewed design, agreed with two conditions: fallback to nominal for
  checkpoints missing it, and a pure-function test proving this equals a pure
  nominal-only replay) -- both implemented. One existing 13.4 test's fixture
  changed (word-count-only failure -> unknown-speaker structural failure) since
  the old fixture no longer reaches `section_validation_failed` under the new
  accept-and-carry rule; justified in the test's own docstring and in
  task-14.3.md. The -9% systematic undershoot is explicitly **not**
  compensated (per the plan's own instruction) -- left for 14.4b's data.
  Two revert-and-confirm-failure checks done (constants-pin; the core
  accept-vs-hard-fail behavior change). Full suite: **865 passed**, 0 failed
  (850 baseline after 14.2-b + 15 net new). `ruff check app tests scripts`
  clean. Task 14.3 status: done.
- 2026-09-21: PM accepted Task 14.3 (`039bc8d`) with one harmless observation
  (resume loop's carry math adds the last section's delta too, unlike the
  live loop -- confirmed inert, recorded in task-14.3.md, no code change).
  Coder implemented Task 14.4a (`scripts/run_ai_operational_trial.py`
  only): `classify_failure` (infra/content/other from Task 14.2's
  `error_code`, `schema_validation_failed` included as content per Amendment
  B); per-run `call_stats` derived from `metrics.calls[]`; direct-`sqlite3`
  per-section/outline reads (`AIJobOut` never exposes checkpoint data by
  design); `has_outro` false-negative fix (widened markers + an
  outline-objective fallback matching "conclu" as a substring -- verified
  against the real disclosed case from the Phase 13 trial DB, still present
  locally); `--matrix {local,gemini}` (selects `DIE_AI_MODE`, the decision
  rule, and default sample/media behaviour; `--mode` still overrides for raw
  diagnostics); `--with-samples`/`--with-media` for the Gemini matrix;
  `--resume-evidence` for a two-day quota-split matrix; `--reaggregate` (no
  server, no live trial). Evidence/trial-data moved to
  `data/quality_reviews/phase14/gate-b2/` for fresh runs;
  `--reaggregate` still reads an old file's own `data_dir` so the two named
  Phase 13 evidence files keep working from their original location.
  Verification (Coder never runs a live trial, per task-14.4.md):
  `ruff`/`py_compile` clean; `--reaggregate` against both named Phase 13
  files reproduces the exact documented outcomes (local 1/5 complete;
  Gemini 0/2, both `failure_class=other` with the `ProviderUnavailableError`
  message, since `handler_exception` predates 14.2's `error_code` scheme);
  full suite re-run as an extra sanity check (not required, no `app`/`tests`
  files touched): **865 passed**, unchanged from the Task 14.3 baseline.
  Task 14.4a status: done. Task 14.4b (Gate B-2 execution and report) is
  PM's, not started.
