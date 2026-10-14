# Phase 45 — Audit follow-ups

Close BUG-031–034 and ENH-032–033 against the code and phase evidence available on 2026-10-14.

## Acceptance

- Selected script and learning exports refresh after successful manual edits, speaker/cast renames and durable AI jobs.
- Export planning uses a short database read; folder checks and file copies run without the shared DB lock; sync status is committed only for the settings version copied.
- Step 1/7 project-folder and Step 5 Shorts requests pass through `frontend/static/js/api.js`.
- README describes Remotion as the sole video renderer; `docs/api.md` is regenerated from the current OpenAPI schema.
- ROADMAP, TRACKER, HANDOFF and phase states distinguish completed implementation from pending owner Gates B-25–B-28. Create checkpoint tags only for phases documented as complete.
- Defer rebuilding the exe in `dist/` until those gates are accepted.

## Verification

Run focused export/concurrency and pipeline tests, frontend/browser regressions, Ruff, JavaScript syntax checks, Remotion typecheck/Vitest, and the full pytest suite. Use the phase records as evidence for completion tags.
