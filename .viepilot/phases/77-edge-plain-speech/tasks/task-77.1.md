# Task 77.1 — Restore Edge and plain dialogue

Status: implemented, packaged and installed; tests/owner review/git persistence pending. Evidence in [phase state](../PHASE-STATE.md). The bounded [phase plan](../PLAN.md) was executed.

## Paths

Exact allowed paths and per-file purposes are enumerated in PLAN.md. No scene library, export-folder, renderer timing, reference models or unrelated project code changes.

## Implementation Notes

- Remove annotation scheduling at all three entry paths; strip retired tags at durable save, single-line save and synthesis.
- Edge-only schemas/discovery/preview/dispatch, retain word timing sidecars and current voice selection controls.
- Remove UI cue toolbar and local-engine voice design controls; preserve existing autosave/serialization/navigation locks.
- Migration040 owns engine/tag changes and targeted media invalidation in one transaction; backup local DB first.
- Update project state without claiming tests, installed binaries, git persistence or audible acceptance completed when they are not.
