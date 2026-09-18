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
| 13.1 | Install and qualify Ollama/Qwen | in_progress | Gate A |
| 13.2 | Provider-neutral AI gateway | pending | Contract tests |
| 13.3 | Shared transactions and durable jobs | pending | State-machine review |
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
