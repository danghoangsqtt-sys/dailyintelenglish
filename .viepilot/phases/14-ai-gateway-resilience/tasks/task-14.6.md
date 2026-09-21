# Task 14.6 (revised, Amendment D) — Resume Task 13.10, Local-Only

- **Status:** pending (blocked until 14.7, 14.8, and 14.9 are done)
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
- PM:
