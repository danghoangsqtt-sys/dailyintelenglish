# Task 18.2 — Router roles/modes, per-provider budgets, circuit breaker; Gemini provider removed

- **Status:** not started
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** 18.1 accepted
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.2", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.2", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

`AIRouter(primary, fallback, mode)` with modes `local | cloud | cloud_first`. The effective mode is `local` when there's no key or the kill switch is off. Separate time budgets (cloud `AI_CLOUD_DEADLINE_SECONDS`, fallback a fresh `AI_REQUEST_DEADLINE_SECONDS`). The circuit breaker is on the primary, and a config error opens it at once. Per-call `fallback_used` / `fallback_reason` (the class name only). Legacy stored modes migrate (`gemini`→`cloud`, `hybrid`→`cloud_first`). `gemini_provider.py` is deleted. Other files' Gemini comments are left untouched.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

See plan §3 "18.2". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

_pending_
