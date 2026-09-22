# Phase 14 State — AI Gateway Resilience and Section Budget Rebalancing

## Metadata

- **Phase:** 14
- **Slug:** `14-ai-gateway-resilience`
- **Status:** complete
- **Started:** 2026-09-21
- **Closed:** 2026-09-22
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
| 14.7 | Local-only mode, config-first (Amendment D) | Coder | **done** (Amendment F applied; 879 passed, 0 failed) | see task-14.7.md verification |
| 14.8 | Local hardening: over-length sections, consecutive-lines rule (Amendment D) | Coder | **done** (883 passed, 0 failed) | see task-14.8.md verification |
| 14.9 | Gate B-3, local only (Amendment D) | PM | **done** | script gate PASS 5/5 (first time); learning 4/5; media FAIL as declared (measured pace); see `docs/operations/phase14-gate-b3.md` |
| 14.6 (revised) | Resume Task 13.10, local-only rollout (Amendment D) | Both | **done** | Coder side `1c89b6a`/`1f723de` (884 passed, 0 failed); PM side `d5c817e`/`48695ba`/`c6c2f35`; Phase 13 Task 13.10 complete under D11 |
| 14.10 | Pace calibration, measured not assumed (Amendment G) | Coder | **done** (888 passed, 0 failed) | see task-14.10.md verification |
| 14.11 | Learning repair by removal (Amendment G) | Coder | **done** (891 passed, 0 failed) | see task-14.11.md verification |
| 14.12 | Gate B-4, local only (Amendment G) | PM | **done** | script 3/5, both deaths repeated-8-gram (not word count); learning 3/3; media A/V diff 0.00s (D14 confirmed real) but duration FAIL (runner defect, not product); see `docs/operations/phase14-gate-b4.md` |
| 14.4a-d | Runner: apply the level default speed (Amendment H) | Coder | **done** | see task-14.4.md's "14.4a-d" section verification |
| 14.13 | Repetition repair (Amendment H) | Coder | **done** (902 passed, 0 failed) | see task-14.13.md verification |
| 14.14 | Gate B-5, local only (Amendment H, Phase 14 close-out) | PM | **done** | script 5/5 complete + 5/5 pass at 1,000 words (933/969/981/1002/1046); samples 4/4 (first time); learning 5/5; 0 infra; σ 18.9%; repetition repair fired 3x, all 3 completed; media A/V 0.00s, codec pass, duration FAIL (413.3s, -4.3%); verdict FAIL on media duration only; see `docs/operations/phase14-gate-b5.md` |

Execution order (original): 14.1 → 14.2 → 14.3 → 14.4a (Coder, sequential). 14.5 ran in
parallel (PM). 14.4b started after 14.1–14.4a were merged and the PM reviewed the diffs.

**Execution order (Amendment D, complete):** 14.7 → 14.8 → 14.9 → 14.6 (revised), all
done. Task 14.1-b is dropped (D12) and does not appear in this order.

**Execution order (Amendment G, complete):** README copy fix (14.6, done) → 14.10 →
14.11 → 14.12, all done.

**Execution order (Amendment H, complete):** 14.4a-d → 14.13 → 14.14, all done. **Phase
14 is closed** (`docs/operations/phase14-gate-b5.md`) -- see `SUMMARY.md` for the full
close-out record.

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
- 2026-09-21: PM accepted the 14.7-14.9/revised-14.6 task cards and issued
  Amendment E (plan commit `26dae03`, mirrored into task-14.7.md): allowed
  files add `tests/test_thumbnail_service.py`/`tests/test_youtube_service.py`;
  settled the mode-selector (read-only status line) and health-field
  (`cloud_enabled`, drop `gemini_fallback_configured`) choices the card left
  open. Coder implemented Task 14.7: `AI_MODE` defaults `local`, new
  `AI_ALLOW_CLOUD` gate on `set_ai_mode`; Settings page loses the API-key
  section and interactive mode selector; `/api/ai/health` reports
  `cloud_enabled`; Step 2/3 gain a live Ollama-health check that disables
  Generate and shows install/pull guidance (model tag + digest from the
  health response itself, never hardcoded) when Ollama is unreachable or
  the model isn't pulled, injected via plain DOM APIs into the
  `#generate-panel` container both pages already have (no `.html` edit
  needed); `scripts/check_dependencies.py` gains a required `Ollama + model`
  check, the Gemini-key check becomes informational; README/CHANGELOG
  updated (forward-looking sections only); one new local-mode
  `FakeProvider` test for `thumbnail_service` (`youtube_service` already
  had an equivalent from Task 13.7, recorded rather than duplicated). Full
  suite: **877 passed, 1 failed** — the failure is
  `tests/test_ai_jobs_api.py::test_ai_health_never_exposes_the_gemini_key`,
  a file **outside Task 14.7's allowed list**, asserting the now-removed
  `gemini_fallback_configured` field (a mechanical, expected consequence of
  Amendment E's own instruction, missed by the pre-code grep because that
  grep was scoped to files the task already listed). Revert-and-confirm-
  failure done on the `AI_ALLOW_CLOUD` gate. `ruff`/`node --check` clean.
  Also flagged, not fixed (also outside the allowed list): a stale "Pillow +
  Gemini text" badge in `frontend/pages/step6_thumbnail.html`. Task 14.7
  status: **blocked**, requesting a PM amendment for
  `tests/test_ai_jobs_api.py` (one assertion) before it can go to `done`.
- 2026-09-21: PM issued Amendment F (plan commit `ff99679`), reproducing the
  reported 877/1 result and amending Task 14.7's allowed files to add
  `tests/test_ai_jobs_api.py` (test-only) and `frontend/pages/
  step6_thumbnail.html` (copy-only), plus asking for a dedicated
  `test_generate_package_runs_end_to_end_under_ai_mode_local` in
  `tests/test_youtube_service.py` (naming parity with
  `test_thumbnail_service.py`'s new test, even though the pre-existing
  `test_generate_package_local_mode_needs_no_gemini_key` already covered the
  same scenario). Coder applied all three: the stale assertion now checks
  `data["cloud_enabled"] is False`; the badge now reads "Pillow + local AI
  text"; the new YouTube test added. Full suite re-run: **879 passed, 0
  failed**. Task 14.7 status: **done**.
- 2026-09-21: PM accepted Task 14.7 (`d623b29`), pushed `docs/api.md`
  regeneration (no route-doc change) and a rewritten
  `docs/operations/local-ai.md` for the local-only contract (`d5c817e`,
  `48695ba`), and directed the Coder to start Task 14.8 per task-14.8.md.
  Coder implemented it: `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 1` (new
  constant) gives an over-length section one additional, length-only repair
  pass when it is still over `effective_target * (1 + SCRIPT_SECTION_CARRY_CAP)`
  after its one existing semantic repair -- narrower trigger than the ±15%
  budget check, so under-length misses are provably untouched (14.3's
  accept-and-carry for them is unchanged). `prompts/script/section.txt` now
  states the word budget as a hard, pre-computed range and adds an
  "alternate speakers by default" instruction; `prompts/script/repair.txt`
  now shows the measured word count and signed delta and, for an over-length
  miss, instructs trimming specific lines rather than a full rewrite; the
  consecutive-lines structural error now names the offending speaker id and
  approximate line range. Checkpoint `metrics_json` gains two keys
  (`length_repaired`, `words_before_length_repair`) alongside the existing
  `repaired`/`words_before_repair` pair. `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`
  and both word tolerances stay byte-for-byte unchanged (constants-pin test
  extended, revert-and-confirm-failure done). Four new FakeProvider e2e
  tests cover: the length-only pass firing and fixing an over-length
  section; the length-only pass still missing and being accepted off-target
  anyway; a structural error surviving the one semantic repair never
  triggering the length-only pass; and the total repair-call bound
  (`2 * num_sections + 1`) hit exactly and asserted directly against the
  formula. No deviations -- every required-behaviour and verification item
  implemented within the allowed files. Full suite: **883 passed, 0
  failed**. Task 14.8 status: **done**.
- 2026-09-21/22: PM's independent review of `ac61cf8` accepted 14.8's design and
  tests but flagged one CR-02 finding (magic numbers): `prompts/script/section.txt`
  hard-coded its own copy of `SCRIPT_SECTION_WORD_TOLERANCE` as `0.85`/`1.15`
  literals. Fixed as **14.8-b** (`4542b58`): `_generate_section` now computes
  `min_words`/`max_words` from the real constant once and passes both to the
  template; added a regression test asserting the rendered prompt text matches
  values derived from the constant. `pytest tests/test_script_pipeline.py` → 52
  passed. PM then ran **Gate B-3** (Task 14.9, `docs/operations/phase14-gate-b3.md`,
  commit `c6c2f35`): script gate **PASS 5/5 for the first time** (733/744/792/
  782/800 words, all 7 content checks, 0 infra failures, max repair attempts 1,
  per-section deviation σ down to 22.9% from 55.7%; the length-only repair pass
  fired 3 times and trimmed correctly, e.g. 217→80/291→161/411→151 words over
  target). Learning 4/5 (one idiom not in transcript). Media ran to completion but
  FAILED the declared thresholds (301.5s at ~146 wpm vs. the ~100 wpm plan
  assumed; A/V diff 2.48s vs. the 1.0s threshold) -- both now open product
  questions, not silently resolved. Overall Gate B-3 = FAIL (learning + media);
  per plan §12, D11 stands as the owner override regardless, so Task 13.10/14.6
  proceeds.
- 2026-09-22: Coder implemented Task 14.6 (revised) Coder side -- a live,
  no-mock rollback drill (real `uvicorn` server, throwaway `DATA_DIR`, a free
  port, real Ollama stop/start with all 6 documented env vars, real Playwright
  with no route mocking) proved: Ollama stopped → app starts non-blocking,
  `/api/ai/health` reflects it, Step 2/3 disable Generate and show install/pull
  guidance with no Gemini text, non-AI features still work → Ollama started →
  `/api/ai/health`/`/api/tags` both confirm digest `6488c96fa5fa` → a real
  script AI job and a real learning AI job both reached `complete` against real
  Ollama → guidance disappears on reload. Repeated against a freshly-built
  packaged `.exe` with Ollama stopped: same result. `.viepilot/ARCHITECTURE.md`/
  `AI-GUIDE.md`/`PROJECT-CONTEXT.md` updated (every direct Gemini/AI-engine
  mention now states Ollama-local-default/Gemini-dormant; a deliberately bounded
  fix, not a full rewrite of these pre-Phase-13 documents -- recorded as a scope
  call, not a deviation). Full suite: **884 passed, 0 failed**. Commits `4a7383e`
  (plan), `1c89b6a` (implementation). PM accepted (**D16**) with one copy-fix
  request (README's rollback note still pointed at the in-app Settings key form
  that Task 14.7 removed) -- fixed and pushed (`1f723de`). **With 14.6 done,
  Task 13.10 is complete under D11 and Phase 13 closes**: local is the primary
  and only runtime by owner decision; Gate B-3's script gate passed 5/5 under
  the unchanged rule; the residual learning/media gaps carry forward as Phase 14
  tasks 14.10/14.11, re-measured by Gate B-4 (14.12).
- 2026-09-22: The owner delegated the three product decisions Gate B-3 raised
  (pace calibration, A/V padding, learning repair) to the PM, who measured pace
  for real against Edge TTS (5 speeds × the Gate B-3 winning script,
  `data/quality_reviews/phase14/gate-b3/pace-calibration.json`) and recorded
  Amendment G (`fd35485`, plan §13): **D13** replaces the never-achieved
  `CEFR_WORDS_PER_MINUTE`/speed defaults with the measured table (A1/A2 111wpm
  @0.75, B1 125wpm @0.85, B2 132wpm @0.90, C1 145wpm @1.00, C2 159wpm @1.10);
  **D14** requires investigating the real ~2.5s A/V tail before any renderer
  change or threshold re-declaration; **D15** adds learning repair-by-removal
  (drop still-ungrounded/inconsistent items after the one repair, publish only
  if every count still meets `LEARNING_MIN_*`, record `dropped_items` in
  `metrics_json`); **D16** formally closes Phase 13/Task 13.10 as recorded above.
  Coder wrote `task-14.10.md` (pace calibration), `task-14.11.md` (learning
  repair by removal), and `task-14.12.md` (Gate B-4, PM-owned description-only,
  mirroring the task-14.9.md pattern) from plan §13, doc-first and before any
  implementation file is touched -- awaiting PM's review of the three cards
  before starting 14.10.
- 2026-09-22: PM accepted the three cards and the README nit fix, directed the
  Coder to start Task 14.10. Coder implemented it, doc-first: **D14 investigated
  first**, before any `video_service.py` change -- real Gate B-3 media measured
  via `ffprobe` (video 304.00s vs. audio 301.52s, diff 2.48s, matching the PM's
  reported number), directly reproduced against the exact real command shape
  (zero overshoot at 10s, ~2.5s overshoot at real ~300s scale -- confirmed
  scale-dependent, root-caused to `-shortest` flushing B-frame-buffered frames
  after the audio input ends, not a deliberate design element), and the fix
  verified directly (`-t <known audio duration>` instead of `-shortest` ->
  exact match). Decision: fix it (one new parameter threading the already-known
  `audio_jobs.duration_seconds` through); `AV_DIFF_MAX_SECONDS` stays `1.0`,
  unchanged. `CEFR_WORDS_PER_MINUTE`/new `CEFR_DEFAULT_TTS_SPEED` set to D13's
  measured table; the 6 `cefr_*.txt` Pace lines updated to match.
  `SpeakerConfig.speed` becomes an optional `None` sentinel (found: there is no
  UI control for speed anywhere in the app today -- `step1_config.js` hardcoded
  `1.0` at speaker-creation and payload-build time, both now send `null` so the
  server resolves the CEFR-level default; an existing project's stored speed is
  never touched). Running the full test suite surfaced a real ripple the plan's
  fixture-update list had missed -- 9 more `test_script_pipeline.py` tests
  hardcoded a 100-word single section relying on the *old* B1 wpm's arithmetic
  under the default 1-minute test project; fixed at one point of control
  (`make_config`'s own default duration changed from 1.0 to 0.8 minutes, so
  100 target_words is still reached exactly under the new 125 wpm) rather than
  rewriting 9 fixtures, documented honestly in task-14.10.md's Deviations.
  Constants-pin test added for both new tables, revert-and-confirm-failure done.
  Full suite: **888 passed, 0 failed**. Task 14.10 status: **done**.
- 2026-09-22: PM accepted Task 14.10, directed the Coder to continue straight to
  14.11 (noting a process reminder for next time: wait for accept before starting
  the next task -- fine this once since 14.10 was clean). Coder implemented
  Task 14.11, doc-first: `app/services/ai_job_service.py` has no generic
  "merge a key into metrics_json" entrypoint and is outside this task's allowed
  files, so `learning_pipeline.py` gained its own small
  `_record_dropped_items` helper mirroring `record_generation_call`'s own
  read-modify-write shape (via the already-exported `ai_job_service.get_job`)
  rather than adding a function to that file. New pure functions
  `find_removable_failures`/`drop_items` give a structured, per-item view over
  the same grounding/answer-consistency checks `validate_grounding`/
  `validate_answers` already do (not string re-parsing), so the post-repair
  branch can drop exactly the offending vocabulary word / idiom phrase /
  question, then re-run the full, unchanged `validate_pack` on the reduced pack
  -- publish with `dropped_items` recorded if counts/duplicates still pass,
  else fail `pack_validation_failed` exactly as before with the drop summary
  appended to the message tail. A duplicate or count-only failure (nothing
  removable) still hard-fails unchanged -- confirmed the *existing*
  `test_pipeline_fails_transparently_when_repair_also_fails` fixture already
  exercised exactly that path (its only idiom, dropped, would breach
  `LEARNING_MIN_IDIOMS`) with zero fixture changes needed, only strengthened
  assertions. Two new e2e tests (idiom drop, answer-consistency drop) plus
  revert-and-confirm-failure (temporarily forced `removable = []`, confirmed
  both new tests fail for the right reason, restored). Full suite: **891
  passed, 0 failed**. Task 14.11 status: **done**. Per the PM's instruction,
  Coder now stops completely (no pytest, no Ollama) pending Gate B-4 (14.12).
- 2026-09-22: PM accepted Task 14.11 and ran **Gate B-4** (Task 14.12,
  `docs/operations/phase14-gate-b4.md`, commits `e018359`/`c05e1c1`): at the
  corrected 1,000-word B1 target, script **3/5** (991/984/915 words, all
  passing content checks) -- both misses died on `global_validation_failed`
  with the repeated-8-gram check as the **sole** failing check (1.02% and
  4.32% against the unchanged 1% threshold); no job died on word count,
  confirming Task 14.10 solved that failure class. Repair success rate 65%,
  0 infra failures. Learning 3/3. Media: A/V diff **0.00s**, directly
  confirming Task 14.10's D14 fix is real and correct; duration still FAILED
  the threshold, but only because the runner (`scripts/run_ai_operational_trial.py`
  line ~164) hard-codes speaker `"speed": 1.0` for every test speaker, so
  the B1 level default (0.85, Task 14.10) never actually applied to any Gate
  B-4 run even though the real UI already sends no explicit speed and gets
  it automatically -- a runner defect, not a product regression. PM recorded
  **Amendment H** (decisions D17-D18) and authorized two more Coder tasks
  before Gate B-5: **14.4a-d** (runner-only: stop hard-coding speed, record
  each run's resolved speeds in evidence) and **14.13** (repetition repair --
  one targeted repair of the single worst section when a global failure is
  repetition-only, bounded `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 1`,
  section prompt gains a proactive "avoid these repeated phrases" continuity
  note, repair bound becomes `2 * num_sections + 2`). Coder mirrored both into
  a new "14.4a-d" section appended to `task-14.4.md` (matching the existing
  "14.4a-c" sub-round convention already used there) and a new
  `task-14.13.md`, plus `task-14.14.md` (Gate B-5, PM-owned description-only,
  mirroring the `task-14.9.md`/`task-14.12.md` pattern -- **Phase 14 closes
  after Gate B-5 regardless of verdict**) -- doc-first, before any
  implementation file is touched, awaiting PM's review of the cards before
  starting 14.4a-d.
- 2026-09-22: PM accepted the three cards, flagged two implementation notes
  for 14.13 (worst-section attribution by repeated-window *start* position,
  with the checkpoint overwrite explicit on `section_index`; cap the
  continuity-note phrase list with a named constant), and authorized starting
  14.4a-d then 14.13, sequentially, each with its own design/code commit.
  Coder implemented **14.4a-d**: `_speaker_payload()` no longer sends an
  explicit `speed` key at all (matches `step1_config.js`'s own behavior for a
  new speaker); `run_script_trial()`'s evidence record gains
  `speaker_speeds`, read off the server's already-resolved project response.
  `--reaggregate` against the Gate B-4 evidence file reproduced every number
  byte-for-byte (`repair_success_rate=0.65`, both repeated-8-gram messages
  verbatim). Commit `9b8d0be`. Coder then implemented **14.13**: two new pure
  functions -- `find_repeated_8grams_by_section` (attributes each repeated
  8-gram occurrence to the section it *starts* in, so the pipeline can pick
  the single worst section) and `frequent_repeated_phrases` (the proactive
  continuity-note list, capped by a new `SCRIPT_SECTION_AVOID_PHRASES_MAX =
  8`). When a global failure is repetition-only (every hard error starts with
  `"repeated 8-gram ratio"`), the pipeline re-fetches fresh checkpoints,
  regenerates only the worst section through the existing `_repair_section`
  machinery with the actual repeated phrases named, overwrites that exact
  section's checkpoint (upsert on `section_index`, confirmed via
  `ai_job_service.save_checkpoint`'s own `ON CONFLICT` clause), and re-checks
  the global validation once -- bounded by a new
  `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 1`, new bound `2 * num_sections +
  2`. `section.txt` gains a proactive "avoid these repeated phrases" note.
  `SCRIPT_MAX_REPEATED_8GRAM_RATIO` added to the constants-pin test,
  unchanged value. 11 new tests (7 pure-function, 3 e2e for the
  success/still-failing/mixed-never-triggers cases, 1 bound test hitting
  `2n+2` exactly) -- one real bug caught only by running them (the literal
  `REPEATED_PHRASE` test fixture was 7 words, not 8, silently invalidating
  every hand-derived word-count/ratio expectation; fixed, re-ran clean).
  Revert-and-confirm-failure done on both the constants pin and the trigger
  condition itself. Commit `256ba01` (plan) + implementation commit. Full
  suite: **902 passed, 0 failed**. Both 14.4a-d and 14.13 status: **done**.
  Per the PM's instruction, Coder now stops completely (no pytest, no Ollama)
  pending Gate B-5 (14.14) -- **Phase 14 closes after that run regardless of
  verdict**.
- 2026-09-22: PM accepted Task 14.4a-d and Task 14.13, then ran **Gate B-5**
  (Task 14.14, `docs/operations/phase14-gate-b5.md`, commit `e9a013d`): script
  gate **5/5 complete AND 5/5 passing content checks** at the corrected
  1,000-word B1 target (933/969/981/1002/1046 words, σ 18.9% -- down from
  Gate B-2's 55.7%); B1 5/10-minute + A2/C1 samples **4/4** (the first time
  every sample has passed); learning **5/5**; 0 infrastructure failures.
  Task 14.13's repetition repair fired 3 times across the matrix (run 5,
  the B1-10-minute sample, and the C1 sample) and **all 3 of those jobs
  still completed** -- the exact failure class that killed 2/5 jobs at
  Gate B-4 is now neutralized. Media, measured for the first time at the
  real level-default speed (Task 14.4a-d's fix): A/V diff **0.00s** (Task
  14.10's D14 fix reconfirmed at yet another data point), codec checks
  passed, but duration still **FAILED** (413.3s, -4.3% short) -- the
  winning script (933 words) landed at the low end of its own tolerance
  band while the real spoken pace (~135 wpm) runs modestly faster than the
  single-script pace-calibration measurement (125 wpm, D13) predicted; both
  factors compound in the same direction. **Overall Gate B-5 verdict: FAIL,
  on media duration only** -- script/samples/learning all pass outright for
  the first time in this phase's history. Per D11, this remains the owner's
  override regardless: local-only ships either way. **Phase 14 is closed**
  per plan §14 (closes after Gate B-5 regardless of verdict). Coder's final
  task: write `SUMMARY.md`, close out this file (status `complete`, closed
  2026-09-22, full task table), commit, push, and tag both
  `die-vp-p13-complete` and `die-vp-p14-complete` on that commit.
