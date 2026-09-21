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
| 14.4a-c | Runner fixes from the real local Gate B-2 run (media 500, word-count scoring) | Coder | done | `--reaggregate` matches PM's reported numbers |
| 14.4b | Gate B second run, both providers, declared protocol | PM | done | Decision rules in plan §4.4 — result: local FAIL 3/5, Gemini FAIL-INFRA 0/5, stop condition |
| 14.5 | Correct `docs/operations/phase13-acceptance.md` | PM | done | Original text preserved |
| 14.1-b | Gemini backoff redesign (retryDelay, daily-429 no-retry, wider 503 window) | — | **dropped (D12)** | Superseded by the owner's decision to drop Gemini (Amendment D) — never started, no task card was ever created |
| 14.7 | Local-only mode, config-first (Amendment D) | Coder | pending | `--matrix`-style flags n/a; see task-14.7.md verification |
| 14.8 | Local hardening: over-length sections, consecutive-lines rule (Amendment D) | Coder | pending | Depends on 14.7 accepted; constants-pin extended |
| 14.9 | Gate B-3, local only (Amendment D) | PM | pending | Depends on 14.7 + 14.8 done; Coder idle during the run |
| 14.6 (revised) | Resume Task 13.10, local-only rollout (Amendment D) | Both | pending | Depends on 14.7 + 14.8 + 14.9 |

Execution order (original): 14.1 → 14.2 → 14.3 → 14.4a (Coder, sequential). 14.5 ran in
parallel (PM). 14.4b started after 14.1–14.4a were merged and the PM reviewed the diffs.

**Execution order (Amendment D, current):** 14.7 → 14.8 (Coder, sequential; PM reviews
each diff before the next starts) → 14.9 (PM runs; Coder idle) → 14.6 (revised). Task
14.1-b is dropped (D12) and does not appear in this order.
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
- 2026-09-21: PM reviewed `377f140` and found a real logic bug: the Gemini
  decision's original wording ("5/5 complete AND <=1 infra death") is
  self-contradictory (a dead job isn't complete), making the one-death-
  absorbed branch unreachable and mis-labeling a real 1-infra-death+4-pass
  matrix as `FAIL-CONTENT`. PM issued Amendment C (`92baabf`, plan §4.4,
  before any Gate B-2 result existed) with the corrected formula (`infra <=
  1 AND content_pass >= 4 AND completed + infra == n`). Coder fixed
  `gemini_matrix_decision` accordingly, added four worked examples to its
  docstring (no dedicated test file exists for this script), and re-verified
  `--reaggregate` against both named Phase 13 files still prints identical
  decisions (neither file's data happens to exercise the fixed branch, since
  neither has exactly one infra death among 5 runs -- confirms no
  regression, not that the fix was exercised by real data). `ruff` clean.
  Task 14.4a (incl. Amendment C) status: done.
- 2026-09-21: PM ran the real local Gate B-2 matrix (`gate-b2-20260921T080706Z.json`):
  3/5 complete (all 3 pass content), 0 infra, repair_success_rate 44%,
  `FAIL` under 13.9 (needs 5/5) but a real improvement over Phase 13's 1/5 --
  media crashed the run. Found two runner bugs and requested fixes (14.4a-c,
  scripts/run_ai_operational_trial.py only) while running the Gemini matrix
  in parallel (Gemini doesn't touch Ollama, so no `NUM_PARALLEL` conflict;
  the running Python process had already loaded the old file, so editing it
  concurrently was safe). Bug 1: `/audio/generate` requires every line to
  already have `audio_cache_path` (the UI sets this per-line via
  `POST .../tts/preview`, which the runner never called) -- fixed with a new
  `synthesize_all_lines()` called before `/audio/generate`. Bug 2:
  `analyze_script`'s word-count check used the fixed B1-eight-minute 720-880
  range for every run, including the 5/10-min and A2/C1 samples -- fixed
  with `_script_word_range(cefr_level, duration_minutes)`; B1-eight-minute
  scoring is unchanged (reproduces exactly 720-880). Added `--media-only
  PROJECT_ID` and `--reaggregate --media-evidence` so PM can re-test media
  alone without re-running the ~35-40 min script matrix -- required
  extracting the full script+learning+media decision into a shared
  `local_full_decision()` so `main()` and `reaggregate()` can't drift.
  Verified per PM's explicit hold (ruff/py_compile/--reaggregate only, no
  pytest, nothing touching Ollama/Gemini): `--reaggregate` on PM's new local
  file reproduces PM's reported numbers exactly and shows the 3 samples'
  `word_count_in_range`/`all_checks_pass` flipping to the corrected values
  while the 3 B1-eight-minute runs and the overall `FAIL` decision stay
  byte-for-byte unchanged; both named Phase 13 files also unchanged. `ruff`
  clean. Task 14.4a-c status: done, pushed (`dec4913`).
- 2026-09-21: PM ran `--media-only` on the real local Gate B-2 winning
  project (99de9ef7): the media pipeline ran end to end with no server
  error for the first time (59/59 lines synthesized via Edge TTS, mix 200,
  render 200, MP3 361.9s / MP4 364.4s h264/aac) — confirms Task 14.4a-c's
  Bug 1 fix works against a real trial. Media gate still `FAIL` against the
  declared duration/A-V thresholds: 361.9s is outside `[432, 528]` (817
  words spoken at ~135 wpm against the `CEFR_WORDS_PER_MINUTE["B1"]=100`
  planning figure — a pace-calibration question, explicitly out of Phase 14
  scope) and A/V diff 2.52s exceeds the 1.0s threshold (renderer padding).
  `--reaggregate --media-evidence` correctly produced `DECISION: FAIL`.
  Final Gate B-2 result: local FAIL 3/5 (zero infra failures, every
  completed script passed every content check), Gemini FAIL-INFRA 0/5 (503
  storms wider than the 14.1 backoff window; free-tier 20 requests/day
  exhausted by retries, confirmed via a live probe showing `quotaId`
  containing `PerDay`/`FreeTier`, `retryDelay` 21s). This is a stop
  condition under plan §8 -- Task 13.10 stays blocked. PM wrote the full
  report (`docs/operations/phase14-gate-b2.md`, commit `92ca433`) and
  recorded the verdict (commit `ad17925`, then the media addendum in
  `86fa9b3`).
- 2026-09-21: the owner decided to drop Gemini entirely rather than debug
  cloud quota/billing (decisions D9-D12,
  `docs/brainstorm/session-2026-09-21.md` §Addendum) -- local-only for both
  development and packaged builds; Gemini's provider/settings/tests stay in
  the codebase, dormant, re-enabled only via the new `DIE_AI_ALLOW_CLOUD`
  switch plus config; the packaged app requires Ollama to *generate*, not
  to *start*. PM wrote Amendment D (plan §12) and ADR-001 amendment A2
  (commit `94f5e7b`) and instructed the Coder to mirror it into task cards
  **before any code**, per the doc-first gate. Coder wrote
  `task-14.7.md` (local-only config-first UI/settings/health/docs),
  `task-14.8.md` (local hardening: over-length-section length-only repair
  pass bounded by a new `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS=1`, sharpened
  section/repair prompts, consecutive-lines-constant added to the existing
  constants-pin test -- both word tolerances and the consecutive-lines
  limit itself stay unchanged), and `task-14.9.md` (description only --
  Gate B-3, local-only, PM's to run); revised `task-14.6.md` to the
  local-only rollout (Amendment D superseded the original
  evidence-selection table). Updated this file's task table: Task 14.1-b
  marked **dropped (D12)** (never started, no card was ever created), new
  execution order 14.7 → 14.8 (Coder, sequential, PM reviews each) → 14.9
  (PM) → 14.6 (revised). No product code touched -- pure doc-first mirroring,
  awaiting PM's review of the three new/revised cards before Task 14.7
  implementation starts.
