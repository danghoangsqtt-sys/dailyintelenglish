# Phase 13 State — Local-First AI Reliability

## Metadata

- **Phase:** 13
- **Slug:** `13-local-first-ai-reliability`
- **Status:** in_progress
- **Started:** 2026-09-18
- **Closed:** —
- **Controlling plan:** `docs/implementation/phase-13-local-first-ai-reliability.md`
- **Source brainstorm:** `docs/brainstorm/session-2026-09-18.md`
- **Authorization:** user explicitly invoked `$vp-auto` and instructed execution after
  first saving a strict detailed plan.

## Preflight

- Branch: `main`; upstream: `origin/main`.
- Initial worktree: only untracked `docs/brainstorm/session-2026-09-18.md`; no product
  code edits were present.
- Phase 1–12: complete.
- Project `.viepilot/STACKS.md`: absent. Global cache has no FastAPI/aiosqlite/httpx
  stack rule; Phase 13 therefore follows repository `SYSTEM-RULES.md`, pinned package
  APIs, existing project patterns, and official provider documentation. This is an
  explicit preflight warning, not silent assumption.
- Hardware evidence from brainstorm: RTX 3060 12,288 MiB, about 11,343 MiB initially
  free; 31.7 GB RAM, about 21 GB initially free; Ollama not initially installed.

## Task status

| Task | Description | Status | Blocking gate |
|---|---|---|---|
| 13.0 | Baseline, ADR, backup, rollback contract | done | Doc-first passed |
| 13.1 | Install and qualify Ollama/Qwen | done | Gate A passed |
| 13.2 | Provider-neutral AI gateway | done | Contract tests passed |
| 13.3 | Shared transactions and durable jobs | done | State-machine review passed |
| 13.4 | Checkpointed script generation | done | Content validators passed |
| 13.5 | Grounded learning generation | done | Learning quality passed |
| 13.6 | Settings, health, and Step 2/3 job UX | done | Browser recovery passed |
| 13.7 | Gemini fallback and compatibility | done | Forced fallback |
| 13.8 | Automated regression/packaging gate | in_progress | Full suite/build |
| 13.9 | Real no-mock bake-off and operational trial | pending | Gate B |
| 13.10 | Rollout, docs, and rollback drill | pending | Release gate |

## Decisions

- Local candidate: `qwen3.5:9b`, 16K context, concurrency one, exact digest pinned only
  after Gate A.
- Automatic cloud fallback: one verified stable Gemini model; preview models excluded.
- Additive migration, atomic final saves, no DB lock during inference.
- Packaged default stays Gemini until external-runtime onboarding is proven.
- Existing synchronous endpoints survive this phase as a compatibility path.

## Evidence log

- 2026-09-18: user authorization received.
- 2026-09-18: `vp-auto` workflow and project rules read.
- 2026-09-18: doc-first controlling plan and phase specification created; no product
  code was modified before this gate.
- 2026-09-18: controlling plan verified at 595 lines with 11 non-placeholder task
  contracts; `git diff --check` clean. Task 13.0 moved to `in_progress`.
- 2026-09-18: Task 13.0 completed. Offline verifier and ruff passed. SQLite Online
  Backup verified byte count/hash/integrity/foreign keys and equal source/backup counts;
  evidence is in `tasks/task-13.0.md`. Task 13.1 moved to `in_progress`.
- 2026-09-19: recovery audit after an abrupt quota stop found Ollama 0.34.2 installed
  and healthy on loopback with cloud disabled and the required user environment saved.
  No model is installed, so Gate A has not run. The WIP qualification runner is lint-
  clean but unexecuted. Detailed Claude handoff saved at
  `docs/handoff/claude-phase13-continuation-prompt.md`; Task 13.1 remains in progress.
- 2026-09-18T23:31Z (session continuation): reviewed the WIP runner and fixed two real
  gaps before the real run — `ollama` CLI PATH resolution (this shell's `PATH` predates
  the winget install; added `resolve_ollama_binary()`), and evidence env vars read via
  a controlled PowerShell User-scope query instead of a stale `os.environ` (added
  `resolved_env()`/`persisted_user_env()`). `ruff` clean. Pulled `qwen3.5:9b` for real
  (digest `6488c96fa5fa`, Q4_K_M, 6.6 GB, matches the plan's expected tag). Ran the real
  qualification: **Gate A PASS, all 9 checks true** (100% GPU offload at 16K context,
  minimum free VRAM 4,370 MiB, minimum free RAM 17,504 MiB, 3/3 schema probes valid,
  cold/warm/model-missing/server-down/stream-close/unload all correct). No memory
  mitigation needed. Evidence:
  `data/quality_reviews/phase13/gate-a/ollama-20260918T233107Z.json` (gitignored). Wrote
  `docs/operations/local-ai.md`. **Task 13.1 moved to `done`.** A second interactive
  Claude Code session was found active on this same working directory mid-task; briefly
  wrote a duplicate near-identical Gate A summary into `tasks/task-13.1.md` before this
  session de-duplicated it — see that file's "Note on concurrent session." No competing
  commit landed on `main` before this session's commit.
- 2026-09-19: user confirmed (after a concurrent-session collision was surfaced and the
  other session's Task 13.1 commit was independently verified and accepted) that this
  session continues Phase 13 alone from Task 13.2 onward; the other session was asked
  to stand down. Live-reverified `gemini-3.8-flash` (real `models.list` call + official
  docs fetch) is still the current stable, non-preview Flash model before locking the
  gateway's Gemini adapter to it. Wrote the concrete file-level plan for Task 13.2 into
  `tasks/task-13.2.md` before any product code; Task 13.2 moved to `in_progress`.
- 2026-09-19: Task 13.2 implemented -- typed contracts (`AIMode`, `GenerationRequest`,
  `GenerationResult`, `Provider` protocol), `OllamaProvider`/`GeminiProvider` (one
  attempt each, no internal retry), `AIRouter` (mode routing, one same-provider
  retry, one Gemini fallback in hybrid mode, an in-process circuit breaker, an
  overall `deadline_seconds` budget via `asyncio.wait_for`), `parse_and_validate`
  shared schema-validation primitive, and a network-free `FakeProvider` for tests.
  New settings (`AI_MODE` default `"gemini"`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
  `OLLAMA_NUM_CTX`, `AI_REQUEST_DEADLINE_SECONDS`) and 7 new typed `Provider*`/
  `SchemaValidationError` exceptions. 43 new tests (contracts/providers/router/
  validation) pass; a revert-and-confirm-failure check on the router's retry bound
  confirmed the "no nested retries" tests are real (4 tests failed for the right
  reason when a 3rd nested retry was intentionally introduced, then passed again
  after reverting). Full suite: **683/683 pass**, 0 flakes. `ruff check .` clean,
  `git diff --check` clean. No legacy route/service touched -- nothing outside this
  package's own tests calls the gateway yet. Task 13.2 moved to `done`.
- 2026-09-19: Found the single DB write-lock is currently a private detail of
  `app/api/projects.py` that 7 other routers + 2 tests import cross-router (43 call
  sites total). Wrote the concrete plan for Task 13.3 (move it to
  `app/db/transactions.py`, add the `ai_generation_jobs`/`ai_generation_checkpoints`
  migration, `ai_job_service.py`'s transition matrix/atomic-claim/lease/recovery/
  cancel design, `ai_worker.py`, `app/api/ai_jobs.py`) into `tasks/task-13.3.md`
  before any code; Task 13.3 moved to `in_progress`.
- 2026-09-19: Task 13.3 implemented -- moved the shared DB write-lock out of
  app/api/projects.py into app/db/transactions.py (7 routers + 2 tests updated,
  zero dual-lock state at any point); added the ai_generation_jobs/
  ai_generation_checkpoints migration (partial unique index for one active job per
  project+operation, full unique index for durable idempotency-key replay);
  ai_job_service.py (explicit transition matrix, atomic conditional-UPDATE claim,
  owner-checked heartbeat, idempotent cancel, bounded recovery); ai_worker.py
  (claim/process lifecycle, idle until Task 13.4/13.5 register a handler, bounded
  graceful shutdown); app/api/ai_jobs.py (202/200 create, null-not-404 for no
  active job, safe AIJobOut projection, GET /api/ai/health that never exposes the
  Gemini key and never fails on Ollama being down). A real event-loop-binding bug
  in AIWorker._stop_event was found via API-level TestClient tests (not caught by
  service/worker unit tests using a single event loop) and fixed by constructing a
  fresh asyncio.Event() in start(); confirmed via revert-and-confirm-failure (the
  same 12 API tests failed identically when reverted, passed again once restored).
  90 new tests across 4 files. Full suite: **753/753 pass**, 0 flakes. `ruff check .`
  clean, `git diff --check` clean, zero stale `_write_lock`/`_write_transaction`/
  `_read_transaction` references anywhere. Task 13.3 moved to `done`.
- 2026-09-19: Wrote the concrete plan for Task 13.4 (checkpointed script pipeline:
  outline/section/repair prompts, script_pipeline.py's pure validators + handler
  orchestration per plan section 6's 8-step sequence, regenerate_line's migration
  onto the Task 13.2 gateway, a small ai_worker.get_db() accessor) into
  tasks/task-13.4.md before any code. Noted explicitly that app/main.py wiring of
  the new handler is out of this task's allowed files and is deferred to Task
  13.6, not silently dropped. Task 13.4 moved to `in_progress`.
- 2026-09-19: Task 13.4 implemented -- script_pipeline.py's 8-step handler
  (outline -> per-section generate/validate/one-repair/checkpoint -> global
  validate -> re-check hash/cancel -> atomic save+status-complete in one
  transaction), 3 new prompts (outline/section/repair), regenerate_line migrated
  onto the Task 13.2 AIRouter (behavior preserved -- all 18 pre-existing
  test_script_service.py tests and all 30 test_script_api.py tests pass
  unmodified), and a small ai_worker.get_db() accessor. 30 new/updated tests
  including 6 full end-to-end handler tests against a FakeProvider-backed router
  (happy path, one-repair-then-succeed, repair-fails-transparently,
  interrupted-then-resumed-from-checkpoint, cancel-before-start,
  stale-on-project-change). Revert-and-confirm-failure on the checkpoint-resume
  logic confirmed that test is real. Full suite: **778/778 pass**, 0 flakes,
  `ruff check .` clean, `git diff --check` clean. app/main.py wiring of the new
  handler deferred to Task 13.6 (not in this task's allowed files) -- recorded,
  not dropped. Task 13.4 moved to `done`.
- 2026-09-19: Found ai_generation_jobs.script_hash_at_start is never populated
  by Task 13.3's create_job()/ai_jobs.py route (neither file is in Task 13.5's
  allowed files either). Wrote the concrete plan for Task 13.5 (learning_pipeline.py
  reuses script_pipeline's normalize_text/compute_config_hash; its own
  start-vs-final-save script-hash comparison substitutes for the unpopulated DB
  column, closing the same race window functionally; grounding/count/duplicate/
  answer validators; one repair pass via a new learning_repair.txt) into
  tasks/task-13.5.md before any code, recording the gap honestly. Task 13.5
  moved to `in_progress`.
- 2026-09-19: Task 13.5 implemented -- learning_pipeline.py's validators
  (grounding/counts/duplicates/answer-consistency), one repair pass via a new
  learning_repair.txt, and a handler mirroring script_pipeline.py's stale/
  cancel/atomic-save structure. Since ai_generation_jobs.script_hash_at_start
  is never populated (job creation is outside this task's allowed files too),
  the pipeline substitutes its own start-vs-final-save script-hash comparison,
  confirmed real via revert-and-confirm-failure. 26 new tests including 7 full
  end-to-end handler tests; all 20 pre-existing test_learning_service.py tests
  and all 22 test_learning_api.py tests pass unmodified. Full suite:
  **794/794 pass**, 0 flakes, `ruff check .`/`git diff --check` clean. Every
  content pipeline Phase 13 planned (script + learning) now exists; neither is
  wired into app/main.py yet (deferred to Task 13.6). Task 13.5 moved to `done`.
- 2026-09-19: Found two real deviations before designing Task 13.6: (1) the
  controlling plan lists a new app/api/ai_health.py, but GET /api/ai/health
  already exists in app/api/ai_jobs.py (built in Task 13.3, before this task's
  file list existed) -- neither creating a duplicate route nor editing
  ai_jobs.py (not in this task's allowed files) is an option, so the existing
  route stays as its implementation; (2) Step 2/3 need near-identical job-
  polling logic, so a new shared frontend/static/js/ai_job.js module is added
  (matches this codebase's existing shared-module precedent) rather than
  duplicating the state machine twice. Both recorded in tasks/task-13.6.md
  before any code. Task 13.6 moved to `in_progress`.
- 2026-09-19: Task 13.6 implemented -- AI mode exposed/validated via
  settings_service.get_ai_mode_status/set_ai_mode/load_ai_mode_from_db and
  PUT /api/settings/ai-mode; app/main.py's lifespan now builds one real
  AIRouter and registers script_pipeline/learning_pipeline handlers on the
  AIWorker before starting it -- both content pipelines are reachable through
  the running app for the first time; Step 2/3 handleGenerate migrated onto a
  new shared frontend/static/js/ai_job.js module (create-or-resume, visible/
  hidden-tab polling backoff, keyboard-accessible cancel) with resume-on-load
  wired into each page's init(). Two real regressions were found and fixed by
  actually running the pre-existing browser suite (not assumed):
  tests/test_keyboard_shortcuts_browser.py and
  tests/test_learning_shell_browser.py both mocked the old synchronous
  generate endpoints. A third real regression was found only in a full-suite
  run: the two new job browser test files' live_server_url fixture leaked a
  background server/DB-singleton connection into
  tests/test_settings_api.py::test_get_reports_env_source_before_anything_is_saved
  (source read "database" instead of "env"); fixed with an explicit
  server.should_exit + thread.join() teardown, confirmed by bisection (807/807
  pass without the two new files present, 819/819 pass with them once the
  teardown was added). A non-obvious JS Promise-auto-flattening bug in
  ai_job.js was found and fixed by reasoning before it could ship (would have
  hung handleGenerate() for the full job duration). Full suite: **819/819
  pass**, 0 flakes (345.22s), `ruff check .`/`git diff --check` clean. Task
  13.6 moved to `done`.
- 2026-09-20 (session continuation after a Codex-quota interruption and handoff):
  re-verified real state before acting -- `git log`/`PHASE-STATE.md` both confirmed
  Tasks 13.0-13.6 already `done` (through commit `336a587`), contradicting the stale
  handoff prompt's description of Task 13.1 as still `in_progress`. Read every
  required doc (AI-GUIDE/SYSTEM-RULES/ARCHITECTURE/TRACKER/ROADMAP/HANDOFF/brainstorm/
  controlling plan/SPEC/ADR-001) plus the actual current `app/services/ai/**`,
  `script_service.py`, `learning_service.py`, `thumbnail_service.py`,
  `youtube_service.py`, `app/api/projects.py`, `app/api/learning.py`, and all four
  services' existing test files before writing Task 13.7's plan. Found two real gaps,
  both recorded in `tasks/task-13.7.md` before any code: (1) migrating the 4 Gemini
  consumers onto the gateway will change/remove the duplicated `_call_gemini`/
  `_generate_with_retry`/`GEMINI_MODEL_FALLBACKS` machinery each of
  `tests/test_script_service.py`, `tests/test_learning_service.py`,
  `tests/test_thumbnail_service.py`, `tests/test_youtube_service.py` currently tests
  directly -- none of those 4 files were in 13.7's original allowed-file list, so the
  list was expanded with reasoning recorded, matching the precedent set in 13.5/13.6;
  (2) live-checked `ai.google.dev/gemini-api/docs/background-execution` (plus a real
  `models.list`/model-metadata call against the configured key) and confirmed Gemini's
  Interactions API background execution is real and lists `gemini-3.8-flash` as
  supported, distinct from `generateContent` -- but wiring it needs
  `app/services/ai_worker.py`/`ai_job_service.py` (to persist/poll
  `ai_generation_jobs.remote_interaction_id`, a column Task 13.3 already added but
  nothing yet reads/writes), neither file in 13.7's allowed list; per ADR-001 point 7
  the existing synchronous foreground call remains valid either way, so this is
  deliberately deferred to a future task rather than expanding scope into worker/job
  files -- the real "architecture change outside allowed files" boundary the user
  asked this session to stop at, resolved by *not* crossing it. Live re-verification
  also reconfirmed `gemini-3.8-flash` is still Google's current non-preview stable
  Flash model one day after Task 13.2's own check. Task 13.7 moved to `in_progress`.
- 2026-09-20: Task 13.7 implemented -- one shared `app/services/ai/router.py::
  build_ai_router_from_settings()` factory (replacing 4 near-identical private
  copies); all 4 direct Gemini consumers (`script_service.generate_script`,
  `learning_service.generate_learning_pack`, `thumbnail_service.generate_suggestions`,
  `youtube_service.generate_package`) migrated off their own duplicated
  `_call_gemini`/`_attempt_model`/`_generate_with_retry`/`GEMINI_MODEL_FALLBACKS`
  transport onto the shared `AIRouter`, each gaining a mode-aware
  `GEMINI_API_KEY`-required guard (only enforced when `AI_MODE=gemini`) and an
  injectable `router` parameter mirroring `regenerate_line`'s Task 13.4 pattern.
  Both legacy synchronous generate routes marked `deprecated=True` (response
  contract unchanged); `docs/api.md` regenerated. A second real gap was found only
  by running the **full** suite after the four service test files were already
  rewritten and green: `tests/test_thumbnail_api.py` and
  `tests/test_youtube_export_api.py` (not in the doc-first plan's expanded
  test-file list either) independently monkeypatched the removed
  `_generate_with_retry` in their own API-level `client` fixtures -- fixed by
  mocking the public `generate_suggestions`/`generate_learning_pack` functions
  instead, recorded in `tasks/task-13.7.md`. Added one `test_ai_router.py` test
  closing a real gap against the "disabled fallback yields a clear local error"
  criterion, and one shared `test_ai_providers.py` wire-payload test protecting
  BUG-011 (`responseJsonSchema` not `responseSchema`) once for all 4 consumers,
  replacing what would have been 4 duplicated per-service versions. `git grep`
  for `_generate_with_retry|_call_gemini|GEMINI_MODEL_FALLBACKS` across
  `tests/`, `app/`, `scripts/` confirmed zero remaining call sites (2 hits left
  are historical docstring mentions, not code). Full suite: **801/801 pass**, 0
  flakes, `ruff check app tests scripts` clean, `git diff --check` clean. Task
  13.7 moved to `done`.
- 2026-09-20: Audited every logger call site across the AI gateway/durable-job layer
  before writing Task 13.8's plan: only `app/services/ai/router.py` (4 sites) and one
  line in `ai_worker.py` log anything at all in this layer today; all already use
  only safe fields, never a raw prompt/response/key. Recorded in `tasks/task-13.8.md`
  before any code. Task 13.8 moved to `in_progress`.
