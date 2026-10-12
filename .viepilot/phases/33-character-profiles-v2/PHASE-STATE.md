# PHASE-STATE — Phase 33: Character Profiles v2

- **Status:** in progress 2026-10-12 (opened by `/vp-auto --phase 33`); was ready to open 2026-10-12 — entry gate met (Gate B-22 PASS 2026-10-12); plan amended with D78–D83 (Amendment A in the plan doc, `docs/brainstorm/session-2026-10-12.md`)
- **Entry gate:** Phase 32 Gate B-22 must be accepted before Task 33.1 starts.
- **Plan:** `docs/implementation/phase-33-character-profiles-v2.md`
- **Scope source:** `docs/brainstorm/session-2026-10-10.md`
- **Owner gate:** B-23 after Task 33.9

This directory is an implementation plan. Creating it does not change the active project phase, the tracker, or Phase 32 status.

| Task | Description | Status | Depends on |
|---|---|---|---|
| 33.1 | Data migration, profile versioning, required gender + sprite facing, and Lina/Alex rehearsal | done 2026-10-12 (`16d8cb1`; rehearsal on a DB copy: Lina/Alex unchanged, 58 sprites, no FK problems; full suite 1660 passed + 1 browser timeout that passes alone) | B-22 ✅ |
| 33.2 | Profile domain service, readiness, lifecycle, and API | done 2026-10-12 (`cc5384a`; `/api/visuals/profiles`; full suite 1674 passed + 1 browser timeout under load that passes alone) | 33.1 |
| 33.3 | Asset slots, prompt pack from Quick create, auto-mapped upload, alignment, approve-once grid | in_progress (backend done; UI in 33.4/33.5) | 33.1, 33.2 |
| 33.4 | Character Library, Quick create, optional wizard sections | in_progress | 33.2 |
| 33.5 | Visual Asset Studio, bulk mapping, and local generation integration | in_progress | 33.3, 33.4 |
| 33.6 | Tiered sprites, renderer compatibility, male-left/female-right placement, mirroring | planned | 33.3, 33.5 |
| 33.7 | Game-style Character Selector in Step 1 (replaces name entry) and Step 5; copy-on-assign defaults | planned | 33.2, 33.4 |
| 33.8 | Dynamic activity, storyboard, and shot integration for 3–6 cast | planned | 33.6, 33.7 |
| 33.9 | Migration rehearsal, regression, real three-character render, Gate B-23 | planned | 33.1–33.8 |

## Locked Phase 33 limits

- Six speakers per project; at most two visible characters per storyboard beat.
- One default outfit per profile.
- Tier 1 has seven approved sprites and enables Talking Starter.
- Lina and Alex retain their IDs and are protected seed profiles.
- One profile can appear only once in a project cast.
- Male left / female right; same gender: speaker 1 left; the side opposite a pack's facing is mirrored (D81–D82).
- Gender is required on every profile; Quick create is the only required creation screen (D79).
- Activity coverage is informative and does not block video readiness.

