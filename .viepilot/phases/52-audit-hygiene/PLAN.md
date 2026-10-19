# PLAN — Phase 52: audit hygiene (2026-10-19)

Status: planned 2026-10-19 from `/vp-audit` → `/vp-evolve BUG-046 BUG-047 BUG-048 ENH-036` (refactor mode). Implementation waits for `/vp-auto --phase 52`.

1. [52.1](tasks/task-52.1.md) — BUG-046 ignore `data/tts_preview/`.
2. [52.2](tasks/task-52.2.md) — ENH-036 Solo editor node IDs, direct layout import, launcher timeout feedback, with regression tests.
3. [52.3](tasks/task-52.3.md) — BUG-048 missing spaces in UI/user docs/state docs; CHANGELOG section order.
4. [52.4](tasks/task-52.4.md) — BUG-047 HANDOFF resume state and phase map; record Phase 52 result. Runs last so it records the final state.

Order: 52.1 and 52.2 are independent; 52.3 before 52.4 (both touch TRACKER/ROADMAP/CHANGELOG). Phase 49 stays the current feature phase (49.10 owner real-art/V49 pending); Phase 52 is independent remediation like Phase 50.

Version: no application bump (behaviour-preserving fixes); record under CHANGELOG `[Unreleased]`. Published 1.4.0-rc.1 / stable 1.3.0 and owner gates (B-25..B-28, V49) unchanged. No EXE rebuild or release.

Risk: low. 52.2 touches the Solo editor and launcher only; text edits in 52.3 must not change identifiers (`front21`, tag names, paths, numeric evidence values).
