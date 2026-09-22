# Task 14.6 (revised, Amendment D) — Resume Task 13.10, Local-Only

- **Status:** in progress (14.7, 14.8, 14.9 all done; Coder started)
- **Owner:** Coder (code/config/packaging/README/CHANGELOG/.viepilot architecture docs);
  PM (`docs/**`, TRACKER, ROADMAP, HANDOFF)
- **Priority:** P2
- **Dependency:** Task 14.7 done; Task 14.8 done; Task 14.9 done (PM's Gate B-3 run)
- **Controlling detail:** plan §12 "14.6 (revised)"; Phase 13 plan §8 Task 13.10;
  `.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.10.md`; ADR-001
  amendment A2; brainstorm decisions D9–D12

## Objective

Ship Task 13.10 (rollout, packaging, documentation, rollback drill) exactly as the Phase
13 plan defines it, with the rollout mode **fixed by the owner's D9–D11 decision**
(local-only) rather than chosen from a Local-vs-Gemini evidence table — Amendment D
superseded the original evidence-selection table entirely (the original table is kept
below, struck through in spirit, for history only — it no longer governs this task).

## Superseded: the original evidence-selection table (Amendment D replaces this)

| Local (Gate B) | Gemini (Gate B-cloud) | Development default | Packaged default |
|---|---|---|---|
| PASS | PASS-cloud | `hybrid` | `gemini` (ADR-001 §6 unchanged) |
| FAIL | PASS-cloud | `gemini`, local labelled experimental | `gemini` |
| PASS | FAIL-INFRA | stop condition: local-only development allowed, packaged rollout blocked | — |
| FAIL | FAIL-INFRA / FAIL-CONTENT | stop condition: 13.10 stays blocked | — |

Gate B-2 landed on the last row (local FAIL 3/5, Gemini FAIL-INFRA 0/5) — a stop
condition under the original table. The owner then decided (D9–D12) to drop Gemini
entirely rather than pursue a Gemini fix, which is what Amendment D and this revision
record.

## Rollout mode (fixed by D9–D11, not chosen from results)

Development default: `local`. Packaged default: `local`. Ollama plus the qualified model
is a **documented prerequisite** for generation; the app still starts without it
(unchanged Phase 13 invariant 9) and shows guidance (Task 14.7). Whether this is an
evidence-backed promotion or an owner override is recorded by Task 14.9's Gate B-3
result, not decided here — this task ships the mode either way, per D11.

## Allowed files

Exactly Task 13.10's list, split by session domain:

- **Coder:** `README.md`, `CHANGELOG.md`, `.env.example`, `scripts/check_dependencies.py`,
  `daily_intel_english_studio.spec`, `scripts/build_exe.ps1` (only if verified changes
  are needed), `.viepilot/ARCHITECTURE.md`, `.viepilot/AI-GUIDE.md`,
  `.viepilot/PROJECT-CONTEXT.md`.
- **PM:** `docs/api.md`, `docs/prompt-guide.md`, `docs/operations/local-ai.md`,
  `docs/operations/phase13-acceptance.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`.

## Actions

Per Task 13.10: install/pull/digest/health/disk/update/uninstall/local-security docs;
missing runtime/model/VRAM guidance surfaced non-fatally (the key check is now
informational only, per Task 14.7). **Rollback drill replaced** (Amendment D): "Ollama
stopped → app starts, AI screens show install/pull guidance, non-AI features work normally
→ Ollama started → generation resumes" — replacing the Phase 13
`hybrid → gemini with Ollama stopped → restart → hybrid` drill, since Gemini is no longer
a supported recovery path (ADR-001 A2 amends Phase 13 invariant 10 accordingly). Packaged
startup non-blocking; mode/model visible in diagnostics; docs reflect only measured
behaviour (cite `docs/operations/phase14-gate-b2.md` and `docs/operations/phase14-gate-b3.md`).

## Verification and exit

Task 13.10's own pass criteria, with the rollback drill above; full suite, `ruff`, JS
`node --check`, dependency check, packaged smoke build green; worktree clean, upstream
set, zero unpushed commits; TRACKER and PHASE-STATE agree on `done` for both Phase 13
(13.10) and Phase 14.

## Execution record

- Coder:
  - Plan/decisions before code:
    1. **Scope of doc edits.** `README.md`, `.env.example`, `scripts/check_dependencies.py`
       were already brought current by Task 14.7 (local-only default, dormant Gemini,
       Ollama required-check) -- re-verify, don't re-write, unless the packaged smoke
       build or the rollback drill below finds an actual gap. `daily_intel_english_studio.spec`
       and `scripts/build_exe.ps1` need no change (Task 14.7 already confirmed
       `httpx` ships as a normal packaged dependency; re-verify via the smoke build
       rather than assume).
    2. **`.viepilot/ARCHITECTURE.md` and `.viepilot/AI-GUIDE.md`/`PROJECT-CONTEXT.md`
       are pre-Phase-13 documents** -- they still describe services calling "Gemini
       API" directly and contain unrelated staleness that predates this entire AI
       Gateway/durable-job architecture (e.g. a fictional SSE "Streaming Progress"
       example in PROJECT-CONTEXT.md, when `ARCHITECTURE.md`'s own System Overview
       section already states "no WebSocket/SSE anywhere in the app"). A full
       modernization of these docs to describe the actual `AIRouter`/checkpointed-
       pipeline architecture is out of this task's scope (13.10's brief is rollout/
       packaging/rollback documentation, not a general architecture-doc accuracy
       pass) and risks introducing new inaccuracies without the same level of
       verification the rest of Phase 13/14 held itself to. **Bounded fix:** update
       every direct Gemini/AI-engine mention (diagram labels, prose, the technology
       decision table, the example API response) to state the AI engine is now
       Ollama (local, default) with Gemini dormant -- mirroring the phrasing already
       used in README.md -- without rewriting the surrounding stale sections. Recorded
       here as a deliberate, bounded scope call, not a deviation requiring a PM
       amendment (no file outside the allowed list is touched).
    3. **Rollback drill design** (Amendment D's replacement drill, per task-14.6.md's
       own Actions section): a real, live drill, not simulated -- a genuine uvicorn
       server (`DIE_DATA_DIR` pointed at a throwaway temp directory, port from
       `_find_free_port()`, never 8000) against the real Ollama binary, which I am
       explicitly authorized to stop/start for this drill. Steps: (a) stop the real
       Ollama process (`ollama` + the `ollama app` tray process, both currently
       running) via PowerShell; (b) confirm `/api/ai/health` reports
       `ollama_reachable: false`; (c) confirm a non-AI feature (project create/list)
       still works; (d) load the real `/step2` and `/step3` pages in a headless
       Playwright browser (no route mocking -- a real server, real health response,
       real JS) and confirm the generate button is disabled and the install/pull
       guidance banner is shown, with no "Gemini" text anywhere in it; (e) start
       Ollama with all 6 documented env vars
       (`OLLAMA_HOST`/`OLLAMA_MODELS`/`OLLAMA_MAX_LOADED_MODELS`/`OLLAMA_NUM_PARALLEL`/
       `OLLAMA_MAX_QUEUE`/`OLLAMA_NO_CLOUD`, per `docs/operations/local-ai.md` §2) set
       on the `ollama serve` process explicitly; (f) confirm `/api/ai/health` and the
       real Ollama `/api/tags` both report digest `6488c96fa5fa`; (g) create a script
       AI job and a learning AI job against the real backend/real Ollama and wait for
       both to reach `complete`; (h) reload `/step2` and confirm the guidance is gone
       and the button is enabled again. Implemented as a one-off script (not part of
       the committed test suite -- it drives a real external process and takes
       minutes, unlike the FakeProvider-backed pytest suite), with every command and
       result transcribed into this card afterward, matching the plan's "no DB
       repair/data loss" and "docs reflect only measured behaviour" requirements.
    4. **Packaged smoke build:** build via `scripts\build_exe.ps1` (already correct
       per item 1), then launch the built exe with Ollama stopped and confirm it
       starts non-blocking and shows the same guidance as the drill above, before
       Ollama is started again for the rest of the drill.
    5. **CHANGELOG.md:** one new entry recording the local-only rollout/rollback-drill
       result, at the top of `[Unreleased]`, matching the existing 14.7 entry's style.
  - Commands and results:
  - Deviations:
  - Revert-and-confirm-failure evidence: N/A for this task -- no new gating logic is
    added (13.10 is docs/packaging/rollback verification, not new pipeline code); the
    rollback drill's own pass/fail *is* the verification, recorded below.
  - Commit(s):
- PM:
