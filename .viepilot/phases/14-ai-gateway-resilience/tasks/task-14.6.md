# Task 14.6 — Resume Task 13.10 with an Evidence-Selected Rollout Mode

- **Status:** pending (blocked until 14.4b and 14.5 are done)
- **Owner:** Coder (code/config/packaging/README/CHANGELOG/.viepilot architecture docs);
  PM (`docs/**`, TRACKER, ROADMAP, HANDOFF)
- **Priority:** P2
- **Dependency:** 14.4b decisions for both providers; 14.5 done
- **Controlling detail:** plan §6 Task 14.6; Phase 13 plan §8 Task 13.10;
  `.viepilot/phases/13-local-first-ai-reliability/tasks/task-13.10.md`

## Objective

Ship Task 13.10 (rollout, packaging, documentation, rollback drill) exactly as the Phase
13 plan defines it, with the development/packaged AI mode chosen from Gate B-2 evidence
rather than from an unverified assumption about the primary provider.

## Allowed files

Exactly Task 13.10's list, split by session domain:

- **Coder:** `README.md`, `CHANGELOG.md`, `.env.example`, `scripts/check_dependencies.py`,
  `daily_intel_english_studio.spec`, `scripts/build_exe.ps1` (only if verified changes
  are needed), `.viepilot/ARCHITECTURE.md`, `.viepilot/AI-GUIDE.md`,
  `.viepilot/PROJECT-CONTEXT.md`.
- **PM:** `docs/api.md`, `docs/prompt-guide.md`, `docs/operations/local-ai.md`,
  `docs/operations/phase13-acceptance.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`.

## Rollout mode by evidence (declared in the plan, not chosen after results)

| Local (Gate B) | Gemini (Gate B-cloud) | Development default | Packaged default |
|---|---|---|---|
| PASS | PASS-cloud | `hybrid` | `gemini` (ADR-001 §6 unchanged) |
| FAIL | PASS-cloud | `gemini`, local labelled experimental | `gemini` |
| PASS | FAIL-INFRA | stop condition: local-only development allowed, packaged rollout blocked | — |
| FAIL | FAIL-INFRA / FAIL-CONTENT | stop condition: 13.10 stays blocked | — |

## Actions

Per Task 13.10: install/pull/digest/health/disk/update/uninstall/local-security docs;
missing runtime/model/VRAM/key guidance surfaced non-fatally; rollback drill
`hybrid → gemini with Ollama stopped → restart → script + learning succeed → hybrid`
without DB repair; packaged startup non-blocking; mode/model visible in diagnostics;
docs reflect only measured behaviour (cite `docs/operations/phase14-gate-b2.md`).

## Verification and exit

Task 13.10's own pass criteria; full suite, `ruff`, JS `node --check`, dependency check,
packaged smoke build green; worktree clean, upstream set, zero unpushed commits; TRACKER
and PHASE-STATE agree on `done` for both Phase 13 (13.10) and Phase 14.

## Execution record

- Coder:
- PM:
