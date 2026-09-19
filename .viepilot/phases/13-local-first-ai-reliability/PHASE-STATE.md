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
| 13.3 | Shared transactions and durable jobs | in_progress | State-machine review |
| 13.4 | Checkpointed script generation | pending | Content validators |
| 13.5 | Grounded learning generation | pending | Learning quality |
| 13.6 | Settings, health, and Step 2/3 job UX | pending | Browser recovery |
| 13.7 | Gemini fallback and compatibility | pending | Forced fallback |
| 13.8 | Automated regression/packaging gate | pending | Full suite/build |
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
