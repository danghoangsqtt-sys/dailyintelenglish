# Task 34.6: Verification and close

## Plan

1. Full pytest and Vitest suites (no behaviour changed; the counts should match 34.0).
2. `ruff check app scripts tests` clean.
3. `/vp-audit --tier1 --tier2`: none of the five findings comes back.
4. Requests BUG-024, BUG-026, ENH-024, ENH-025 and ENH-026: status done with a Resolution line.
5. TRACKER, ROADMAP and PHASE-STATE: Phase 34 complete; CHANGELOG `[Unreleased]` gets one housekeeping entry.
6. Tag `die-vp-p34-complete` (push after the owner OKs it, together with the 34.2 tags).

## Paths

- `.viepilot/TRACKER.md`
- `.viepilot/ROADMAP.md`
- `.viepilot/phases/34-project-hygiene/PHASE-STATE.md`
- `.viepilot/requests/BUG-024.md`
- `.viepilot/requests/BUG-026.md`
- `.viepilot/requests/ENH-024.md`
- `.viepilot/requests/ENH-025.md`
- `.viepilot/requests/ENH-026.md`
- `CHANGELOG.md`

## Verification

The close-out TRACKER entry quotes the audit result and the suite counts.
