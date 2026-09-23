# Task 18.3 — Settings (key/URL/model, test connection), health fields, privacy note

- **Status:** not started
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** 18.2 accepted
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.3", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.3", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

The Settings API and page hold base URL, model and a write-only key (status: set + last 4 characters; clearable), a mode selector, a Test-connection button, and the privacy note. DB values override the `.env` defaults and take effect without a restart. The old `gemini_api_key` row is ignored. `/api/ai/health` adds `cloud_configured`, `cloud_model`, `effective_mode` and `circuit_open`, with no key material.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

See plan §3 "18.3". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

_pending_
