# Task 33.9 — Regression, real project, and Gate B-23

## Objective

Prove migration safety and the complete owner workflow, then obtain owner acceptance before closing Phase 33.

## Paths

- `docs/operations/phase33-character-profiles-acceptance.md`
- `tests/test_character_profiles_migration.py`
- Existing character, project, sprite, activity, storyboard, shot, video-props, and browser suites

## Execution Plan

1. Rehearse migration on a timestamped copy of the real DB and relevant asset roots; record before/after IDs, counts, foreign-key checks, and checksums for Lina/Alex current assets.
2. Through the UI, create a third profile, upload an external identity/core set and Tier 1 sprites, approve them, configure voice defaults, and resume the wizard after a browser restart.
3. Assign Lina, Alex, and the new profile to a three-speaker project; verify copy-on-assign settings and project overrides.
4. Render a still-scene video and Talking Starter video; verify active-speaker pairing, captions/audio continuity, sprite fallbacks, and activity cutaways.
5. Re-render an old Lina/Alex project and compare cast IDs, voice settings, and selected assets.
6. Present the Character Library, wizard, selector, and both videos to the owner at Gate B-23.

## Verification

- Run the full Python and browser suite once after targeted suites pass.
- Run frontend syntax checks, Ruff on changed Python, migration foreign-key checks, and one real Remotion render per acceptance mode.
- Record commands, versions, durations, and artifact paths in the acceptance report.

## Acceptance Criteria

- [ ] Migration rehearsal has no lost or orphaned data.
- [ ] The third profile is created without filesystem manipulation.
- [ ] A three-speaker project uses the intended profile for every speaker and the intended pair for every beat.
- [ ] Old Lina/Alex project behavior remains stable.
- [ ] Owner accepts Gate B-23; only then may Phase 33 be marked complete.

