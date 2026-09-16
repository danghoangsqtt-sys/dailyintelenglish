# Phase 4 State — Post-v1.0.0-beta Polish

## Metadata
- **Phase:** 4
- **Slug:** 04-post-beta-polish
- **Status:** in_progress
- **Started:** 2026-09-15
- **Milestone Progress:** 2 / 3 tasks done — 4.1 CEFR `news` prompt tuning done
  2026-09-15 (partial, honestly-reported improvement — see `tasks/task-4.1.md`); 4.4 P0
  navigation bug fixes done 2026-09-16 (see below); 4.2 UI Redesign Slice 2 (7 pages) in
  progress, 4/7 pages done (Learning, TTS, Video, Thumbnail), 4.2e (YouTube) now in
  progress, handed to Codex. New phase,
  scoped in the 2026-09-15 brainstorm session (`docs/brainstorm/session-2026-09-15.md`),
  not part of the original 21-day/3-phase plan. Progress cancellation and real
  LivePortrait lip-sync remain explicitly deferred, not part of this phase. A new
  Task 4.3 (Vietnamese UI localization) is scoped and queued to start once Task 4.2's
  remaining 5 pages are done — see `docs/brainstorm/session-2026-09-15.md`'s
  2026-09-15 update.
- **Test Suite Status:** 560/560 pass (2026-09-16, after Task 4.2d) — see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 4.1: CEFR `news`-genre prompt tuning — ✅ DONE (2026-09-15), partial improvement
- **Status:** done
- Added register-vs-complexity guidance to `prompts/script/news.txt`. Re-tested A2/B1/B2
  × `news` (3 real Gemini calls) against Task 2.1b's exact rubric: one specific failure
  pattern (A2's indefinite-pronoun+modal) didn't recur, but Future Simple usage persists
  at A2, the exact flagged idiom ("a breath of fresh air") recurred verbatim at B1, and
  B2's grammar still borders C1 (Past Perfect Continuous) though idiom choice improved.
  Honestly reported as partial/mixed, not a full fix — consistent with tuning a
  probabilistic model. See `tasks/task-4.1.md` for the full evidence.

### Task 4.2: UI Redesign Slice 2 (7 remaining pages)
- **Status:** in_progress (4/7 pages done)
- Split into per-page sub-tasks, written doc-first individually as each is picked up.
- **4.2a — Learning (`/step3`)**: ✅ DONE (2026-09-15). Wrapped in the same 3-panel
  shell as Script (Task 2.4), no timeline (confirmed decision — Learning has no
  sequential-items concept). New read-only item inspector (click a vocabulary/idiom/
  grammar/quiz card to see its full detail; quiz inspector always shows the answer,
  independent of the main list's toggle) — no fake per-item actions invented, since no
  backend supports regenerating a single item. Existing inline-edit/autosave/tabs
  behavior unchanged. First browser test coverage this page has ever had (3 new tests).
  Found and fixed a real regression during verification: `test_step_nav_browser.py`
  assumed only Script used the shell layout, and `step3_learning.js`'s `StepNav.render()`
  call was missing `variant: "workflow"` — both fixed at the root cause. 536/536 full
  suite passes (up from 533). See `tasks/task-4.2a.md` for the full record.
- **4.2b — TTS Audio Studio (`/step4`)**: ✅ DONE (2026-09-16), implemented by Codex,
  accepted by PM (Claude Code) per AR-06 — first task delegated to Codex since its quota
  was restored. Shell + 3-track timeline (Script/Voice/Music); read-only inspector shows
  the selected line, an honest session-only preview-state badge (Not previewed/
  Synthesizing/Preview ready — never guesses persisted cache state), a real Listen
  action reusing the existing preview endpoint, and a real scroll-to-speaker-card "Voice
  settings" affordance (no new write path). Existing per-speaker autosave debounce and
  the sequential Generate-All request order are unchanged. 5 new browser tests.
  **2 real review rounds**: (1) Codex correctly flagged and PM pre-authorized a narrow
  fix to `test_step_nav_browser.py` (same `variant:"workflow"` class of issue as 4.2a,
  now covering `current_step == 4` too) before writing any other code; (2) PM's
  independent screenshot review (not the test suite) caught a real bug — `renderTimeline()`
  cleared the Script/Voice lanes on every re-render but never the Music lane, so it
  accumulated duplicate clips — sent back to Codex with the exact fix, which PM then
  re-verified independently (including a 5-interaction stress-test screenshot) before
  accepting. 541/541 full suite passes. See `tasks/task-4.2b.md` for the full record.
- **4.2c — Video Studio (`/step5`)**: ✅ DONE (2026-09-16), implemented by Codex,
  accepted by PM per AR-06 — second task delegated end-to-end to Codex. Shell + real
  3-track timeline built from data this page didn't previously fetch (`Api.getScript()`
  added, correlated to the audio job's real per-line `timestamps` by array index).
  Script track is a read-only reference; Voice track honestly shows "Synced" (every
  line's audio already exists by this stage, unlike TTS's in-progress states); Music
  track shows the real `background_music` filename or "No music selected". Read-only
  inspector shows real `M:SS – M:SS` measured timing — no playback button (a considered,
  disclosed scope cut: added seek/race complexity wasn't worth it for an optional
  feature). `renderTimeline()` proactively clears all 3 lanes before every re-render,
  directly avoiding Task 4.2b's exact bug class. A `/script`-fetch failure degrades
  gracefully (logs, shows a timeline-only message) rather than blocking the core
  avatar/template/generate workflow — deliberately designed this way because the
  pre-existing `tests/test_video_studio_browser.py` (out of scope, not touched) uses a
  fake project ID that would otherwise hit a real 404. 4 new browser tests, plus the
  same pre-authorized `test_step_nav_browser.py` one-line extension
  (`current_step == 5`). **Zero real defects found on PM review this round** — the
  accumulated task-card warnings about Task 4.2a/4.2b's 2 prior regressions appear to
  have worked; PM still independently re-verified everything including a 6-interaction
  stress-test screenshot of the Music lane. 544/544 full suite passes. See
  `tasks/task-4.2c.md` for the full record.
- **4.2d — Thumbnail Generator (`/step6`)**: ✅ DONE (2026-09-16), implemented by
  Codex, accepted by PM per AR-06 — third task delegated end-to-end to Codex. Shell, no
  timeline (same as Learning — no sequential-items concept). One important difference
  from every prior sub-task: this page already had a real, pre-existing write-path
  editor for the selected item (headline + color palette, 400ms debounced autosave,
  trailing-save coalescing, 409 stale-revision conflict handling, SaveIndicator,
  beforeunload guard) — the inspector pane hosts this real editor as-is, not a new
  read-only view, since the write path already existed and wasn't invented. Stage
  hosts template selection + variant grid; every existing element id preserved
  unrenamed. 2 new browser tests (`test_thumbnail_shell_browser.py`) — real
  mouse-driven resize of both panes, sidebar collapse/re-expand, and a combined
  headline+color edit within one debounce window asserting exactly 1 `PATCH` fires.
  Plus the same pre-authorized `test_step_nav_browser.py` one-line extension
  (`current_step == 6`). **Zero real defects found on PM review** — PM independently
  re-ran every verification command, read the full diff (confirmed every required
  element id survived, and that CSS custom-property renames were true pre-existing
  aliases in `style.css`, not a functional change), and ran its own disposable script +
  screenshots in both themes beyond what was asked (confirmed keyboard-driven resize
  works, and that the relocated preview — flagged as an open risk at plan-review time —
  stays visually usable in the narrower inspector). 560/560 full suite passes. See
  `tasks/task-4.2d.md` for the full record.
- **4.2e — YouTube Package (`/step7`)**: 🔄 IN PROGRESS (2026-09-16), handed to Codex
  as Implementer per AR-06. Shell, no timeline. Real design question different from
  every prior sub-task: this page has no per-item selection concept at all (titles,
  description, chapters, tags are all fully shown at once, not click-to-select), so
  there's no natural "selected item" for the inspector. Decision: inspector hosts the
  "Full Package Export" section (real dynamic readiness state — video + thumbnail
  present or not) as a persistent workflow-status panel, not an item detail view; the 3
  title-variant cards deliberately do NOT get a click-to-inspect interaction invented
  for them (would be a new feature, not a structural move). See `tasks/task-4.2e.md`
  for the full plan.
- Remaining after 4.2e: Music Library, Step1-Config — not started (both deliberately
  NOT shell-based, per the 2026-09-14 session decision).

### Task 4.4: P0 navigation bug fixes (Dashboard Continue + Config duplicate-project) — ✅ DONE (2026-09-16)
- **Status:** done
- Inserted ahead of Task 4.2d after a Codex read-only UI audit found 2 real P0 bugs,
  both independently confirmed by PM: (1) Dashboard's "Continue" button silently no-ops
  for `audio_generated`/`video_generated`/`complete` project statuses — only
  `draft`/`script_generated` were ever wired up; (2) the Config page (`/step1`) ignores
  an existing `project_id` in the URL and always creates a brand-new project on submit,
  even though StepNav makes Config a real, reachable link from every other step —
  meaning a user revisiting Config on an in-progress project can silently spawn a
  duplicate. Implemented by Codex, accepted by PM per AR-06. Fix uses only existing
  backend capability — extended `dashboard.js`'s Continue handler to a `STATUS_TO_STEP`
  map for all 5 statuses; `step1_config.js` now fetches+prefills via `Api.getProject()`
  and saves via a new `Api.updateProject()` (`PUT /api/projects/{id}`, previously
  implemented but never called from the frontend) when the project is still `draft`,
  and renders every control disabled with a locked-configuration banner for any later
  status — no cascade/regenerate logic invented. 5 new browser tests
  (`test_step1_config_edit_browser.py`) including a double-submit stress test and a
  parametrized all-4-statuses read-only-lock check; 2 extended
  (`test_dashboard_browser.py` now parametrized across all 5 statuses plus a defensive
  unknown-status no-op test). **Zero real defects found on PM review** — PM
  independently re-ran every verification command, read the full diff, and ran its own
  disposable script + screenshot beyond what was asked (confirmed a disabled chip
  button truly can't be clicked via a forced DOM event, not just via Playwright's
  convenience checks). 558/558 full suite passes (up from 555). See `tasks/task-4.4.md`
  for the full record. Resuming Task 4.2 with sub-task 4.2d (Thumbnail) next.
