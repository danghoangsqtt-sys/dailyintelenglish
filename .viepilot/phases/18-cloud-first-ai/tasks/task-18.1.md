# Task 18.1 — `OpenAICompatProvider`

- **Status:** not started
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** none (the phase starts after Phase 17 closes)
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.1", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.1", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

One HTTP call per `generate()` to `{base_url}/chat/completions`. Plain prompt-only JSON (never `response_format`). `reasoning: {exclude: true}`. Fence strip. Error mapping per plan §3 18.1: 200-with-error / 429 / 5xx are transient; 401/402/403/404 are a config error; timeout; invalid shape. The key is never in messages or logs.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

See plan §3 "18.1". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

_pending_
