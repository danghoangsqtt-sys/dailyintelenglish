# Task 33.9 — Regression, real project, and Gate B-23

## Objective

Prove migration safety and the complete owner workflow, then obtain owner acceptance before closing Phase 33.

## Paths

- `docs/operations/phase33-character-profiles-acceptance.md`
- `.viepilot/phases/33-character-profiles-v2/PHASE-STATE.md`
- `.viepilot/TRACKER.md`
- `.viepilot/ROADMAP.md`
- `.viepilot/HANDOFF.json`
- `CHANGELOG.md`
- `scripts/migrate_character_profiles_v2.py`
- `scripts/run_phase33_acceptance.py`
- `app/services/video_renderer_remotion.py`
- `app/services/visuals/sprite_plan.py`
- `video-renderer/src/types.ts`
- `video-renderer/src/spriteTimeline.ts`
- `video-renderer/src/Sprites.tsx`
- `tests/test_character_profiles_migration.py`
- `tests/test_sprite_plan.py`
- `tests/test_sprite_video_props.py`
- `video-renderer/src/spriteTimeline.test.ts`
- `video-renderer/src/Sprites.test.tsx`
- `frontend/pages/characters.html`
- `tests/test_library_grid_browser.py`
- `tests/test_visuals_project_browser.py`
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

- [x] Migration rehearsal has no lost or orphaned data.
- [x] The third profile is created without filesystem manipulation.
- [x] A three-speaker project uses the intended profile for every speaker and the intended pair for every beat.
- [x] Old Lina/Alex project behavior remains stable.
- [ ] Owner accepts Gate B-23; only then may Phase 33 be marked complete.

## Implementation Notes

- Never run the rehearsal against the live database or mutate the owner's active asset folders; use a timestamped isolated copy.
- Keep Phase 32 Gate B-22 pending and keep Phase 33 open until the owner explicitly accepts Gate B-23.
- Separate automated proof, generated acceptance artifacts, and owner visual review in the report so a passing test is not recorded as owner acceptance.
- Preserve any existing project/profile data used for comparison and record hashes before and after the rehearsal.

### Owner review remediation — 2026-10-10

The first owner review found two composition defects in the Talking Starter render. Activity cutaways covered the active speaker, and the same two characters could exchange left/right positions when a storyboard beat stored the pair in a different order.

- `video-renderer/src/Sprites.tsx`: draw activity cutaways with the scene plates, before the sprite layer, so the visible speaker and listener remain on screen.
- `video-renderer/src/spriteTimeline.ts`: canonicalize every two-character pair by cast slot before assigning left/right stage positions.
- `video-renderer/src/spriteTimeline.test.ts`: pin both the stable pair order and the cutaway/sprite layer order.
- `docs/operations/phase33-character-profiles-acceptance.md`: record the remediation and replacement render evidence.
- `scripts/run_phase33_acceptance.py`: update only if the existing acceptance runner cannot produce the required replacement frames and video.

Verification: run focused Vitest tests, the full renderer Vitest suite, TypeScript typecheck, render the real three-character Talking Starter video again, and visually inspect a cutaway frame plus frames on both sides of a speaker change. Gate B-23 remains pending owner acceptance.

## Automated Acceptance Result — 2026-10-10

- Fresh copied-data migration passed with 0 foreign-key errors, unchanged Lina/Alex IDs, cast rows, speaker settings and file hashes; 58 legacy sprite files were registered.
- UI rehearsal created and locked Rowan with 5/5 core and 7/7 Talking Starter assets, including a browser-context restart between creation and resume.
- Three Remotion renders completed without fallback: three-cast still, three-cast talking, and the old Lina/Alex project.
- Acceptance exposed and fixed a real 3+ cast renderer defect: only slots 0/1 were loaded. Props and Remotion now carry slots 0–5 and show each approved storyboard pair.
- Evidence and commands are recorded in `docs/operations/phase33-character-profiles-acceptance.md`.
- Final full suite: 1,674 passed, 7 skipped, 0 failed; Vitest: 66 passed; TypeScript and changed-file Ruff clean.
- Owner-review remediation keeps the active speaker above activity cutaways and canonicalizes every pair by cast slot so Alex/Lina do not exchange sides when the active speaker changes. Replacement render passed without fallback; Vitest is now 67 passed across 10 files and TypeScript remains clean.
- Gate B-23 remains pending explicit owner review; Task 33.9 stays `in progress`.
- Skills applied: `vp-auto@0.2.2`.

