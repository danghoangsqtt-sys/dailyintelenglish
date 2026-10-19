# SUMMARY — Phase 52: audit hygiene

Planned and implemented 2026-10-19 from `/vp-audit` → `/vp-evolve` → `/vp-auto --phase 52`. Refactor, no version bump.

| Task | Request | Result |
|---|---|---|
| 52.1 | BUG-046 | `data/tts_preview/` ignored |
| 52.2 | ENH-036 | Diagram node IDs kept by label (edges no longer reconnect); direct layout-checker import; launcher writes a manual-open hint on readiness timeout (still never opens an unverified port) |
| 52.3 | BUG-048 | Missing spaces before numbers fixed in UI string, user docs and state docs (spaces only, hunk-checked); CHANGELOG Phase 49 block moved under `[Unreleased]` |
| 52.4 | BUG-047 | Stale HANDOFF `feature_plan.note` fixed; "missing phases 47–50" was an audit false positive |

Full pytest 1886 passed in 789.26s (1884 + 2 new regression tests); renderer 124 Vitest passed; Ruff and `node --check` clean.

Unchanged: Phase 49.10 owner real-art/V49 gate, owner gates B-25..B-28, published 1.4.0-rc.1 and stable 1.3.0, installed EXE.
