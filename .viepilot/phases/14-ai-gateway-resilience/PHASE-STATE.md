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
| 14.2 | Job telemetry: repair/fallback/provider/attempts/error codes | Coder | pending | Row fields written; `provider_*` codes |
| 14.3 | Running section budget; hard gate only at global ±10% | Coder | pending | Constants pinned; carry/resume tests |
| 14.4a | Runner preparation (classification, per-section stats, aggregates) | Coder | pending | Reaggregate dry run |
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
