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
| 33.3 | Asset slots, prompt pack from Quick create, auto-mapped upload, alignment, approve-once grid | done 2026-10-12 (`9f746b5`, `0cc1537`; 29 slots, rename/align/check/review; real Alex 28/28; owner tried Jack in the sandbox: "rất tốt") | 33.1, 33.2 |
| 33.4 | Character Library, Quick create, optional wizard sections | done 2026-10-12 (`c6dea48`; Profiles tab, Quick create, optional details; old tabs kept) | 33.2 |
| 33.5 | Visual Asset Studio, bulk mapping, and local generation integration | done 2026-10-12 (`c6dea48`; slot cards with input picture, region, prompt, drop zone, review; local generation stays on the old tab, deferred) | 33.3, 33.4 |
| 33.6 | Tiered sprites, renderer compatibility, male-left/female-right placement, mirroring | done 2026-10-12 (`aac3c8a`, `af62eac`; men left / women right, mirroring, slot uploads → sprite_set.json, derived face references D87) | 33.3, 33.5 |
| 33.7 | Game-style Character Selector in Step 1 (replaces name entry) and Step 5; copy-on-assign defaults | done 2026-10-12 (`f13f13d`, `4fbe547`; selector in Step 1 and Step 5, no cast by name, compact speaker cards D88; full suite 1717 passed) | 33.2, 33.4 |
| 33.8 | Dynamic activity, storyboard, and shot integration for 3–6 cast | done 2026-10-12 (`87efc1c`; segments with two on screen, storyboard most-active pair; full suite 1725 passed) | 33.6, 33.7 |
| 33.9 | Migration rehearsal, regression, real three-character render, Gate B-23 | owner 2026-10-13: "video rất tốt" (cast, placement, mirroring pass); missing illustrations/vocabulary traced: no learning content in the gate project, the only insert named an activity the library lacks -> 33.10 | 33.1–33.8 |
| 33.10 | Gate B-23 fixes: storyboard inserts name a library activity, Step 5 names inserts without a picture (`dba9e18`); D102 draw the missing illustrations (local GPU + outside-AI slot, approve in Step 5) | done 2026-10-13 (coverage service, `activity_illustrations` job, Step 5 cards; 240 visuals/Step 5 tests passed) — the real re-render for the owner is next | 33.9 |

## Locked Phase 33 limits

- Six speakers per project; at most two visible characters per storyboard beat.
- One default outfit per profile.
- Tier 1 has seven approved sprites and enables Talking Starter.
- Lina and Alex retain their IDs and are protected seed profiles.
- One profile can appear only once in a project cast.
- Male left / female right; same gender: speaker 1 left; the side opposite a pack's facing is mirrored (D81–D82).
- Gender is required on every profile; Quick create is the only required creation screen (D79).
- Activity coverage is informative and does not block video readiness.


## Task 33.10 plan (D102, owner 2026-10-13)

Owner: "có thể kết hợp AI tạo ảnh để tạo ảnh minh họa không? không cần hình nhân vật nói ở trong ảnh minh họa chỉ cần ảnh minh
họa cho hoạt động đó và có con người bất kỳ trong ảnh". Choices: local GPU + outside-AI slot; quick approval in Step 5; a Step 5
button (no drawing at render time).

- `app/services/visuals/activity_illustrations.py` (new): `coverage(db, project_id)` -- the per-insert match the
  `/activity-coverage` route computed, plus `suggestions`, the pending picture made for it (`pending`), and the outside-AI
  `prompt`; the route now calls it.
- `app/services/visuals/recipes.py`: `activity_illustration_prompt` (GPU: one ordinary person doing the action, the place, no
  text) and `activity_outside_prompt` (outside AI, 16:9); `ACTIVITY_NEGATIVE`.
- `app/services/visuals/pipelines.py`: job `activity_illustrations` (target = project): text2img 1344x768 for every insert
  with neither an approved match nor a pending picture; each picture is stored with `activity_library.upload_activity_bytes`
  as a pending generic activity (activity = the insert's action, context = its place). Registered in `app/main.py`.
- `app/api/visuals.py`: `POST /api/projects/{id}/visuals/activity-illustrations` enqueues it.
- Step 5: under the coverage line, one card per insert without a picture: closest library activities, the pending picture with
  Approve / Redraw, the outside-AI prompt (copy) and a file drop (uploads as that activity); a "Draw missing illustrations"
  button runs the job with the existing job progress. An approved picture enters the library and matches next time.
- Tests: coverage service, the job with a fake engine, the route, the Step 5 cards (browser).
