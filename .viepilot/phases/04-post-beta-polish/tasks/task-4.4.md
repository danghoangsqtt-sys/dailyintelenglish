# Task 4.4: P0 navigation bug fixes (Dashboard Continue + Config duplicate-project)

## Meta
- **ID**: 4.4 (inserted ahead of Task 4.2's remaining sub-tasks — see Doc-First Gate
  below for why; not part of the original 21-day/3-phase plan, scoped from a real-bug
  finding, same as Task 4.2's own origin)
- **Phase**: 4
- **Status**: in_progress (2026-09-16)
- **Priority**: high (P0 — confirmed real bugs, not polish)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: user ran a Codex-driven **read-only** UI audit (`vp-auto` read-only mode) across
the whole app on 2026-09-16, after Task 4.2c shipped. The audit found 2 real P0 behavior
bugs plus several P1/P2 polish items. PM (this session) independently re-verified both
P0 claims by reading the actual code (not trusting the audit report alone) — both are
confirmed real, see "Current state" below. Given they affect navigation reliability
across *every* already-shipped page (not just one), PM proposed and user approved
inserting this task ahead of Task 4.2d (Thumbnail Generator) rather than deferring to
after all 7 pages are redesigned. P1/P2 findings are logged as backlog in
`.viepilot/TRACKER.md` (Decision Log, 2026-09-16 entry) — explicitly out of scope here.

## Current state (researched before writing this plan — do not re-derive from scratch)

### Bug 1 — Dashboard "Continue" button no-ops for 3 of 5 statuses
`frontend/static/js/dashboard.js:154-159` — the `data-action="continue"` click handler:
```js
if (button.dataset.action === "continue") {
  const project = allProjects.find((p) => p.id === id);
  if (project && (project.status === "draft" || project.status === "script_generated")) {
    window.location.href = `/step2?project_id=${encodeURIComponent(id)}`;
  }
}
```
The button renders unconditionally on every project card (`dashboard.js:49`). For
`audio_generated`, `video_generated`, or `complete` status, the `if` is false and
**nothing happens** — no navigation, no error, no console log. Confirmed live by PM.

Project status values (`dashboard.js:21-27`, `STATUS_LABELS`): `draft`,
`script_generated`, `audio_generated`, `video_generated`, `complete`. Confirmed via
`app/api/projects.py` / `app/api/audio.py` / `app/api/video.py` that the **only**
automatic transitions the backend ever performs are `draft → script_generated`
(`projects.py:84`), `script_generated → audio_generated` (`audio.py:69`), and
`audio_generated → video_generated` (`video.py:72`). **`complete` is never set by any
code path today** — it exists in the label map and dashboard filter but is currently
unreachable. Treat it as a real, declared status to handle defensively, not as evidence
it's used.

The 7 pipeline steps (`frontend/static/js/step_nav.js:3-11`): 1 Config, 2 Script,
3 Learning, 4 Audio, 5 Video, 6 Thumbnail, 7 YouTube.

### Bug 2 — Config page always creates a new project, ignores `project_id`
`frontend/static/js/step1_config.js`:
- Line 338: `project_id` from the URL query string is read **only** to pass to
  `StepNav.render()` for breadcrumb links — never used to fetch or prefill anything.
- Line 313-335 (`handleSubmit`): unconditionally calls `Api.createProject(buildPayload())`
  (line 327) and redirects to the **new** project's id. There is no branch that checks
  for an existing `project_id` or calls any kind of update.
- `frontend/static/js/step_nav.js:4` makes "Config" (step 1) a real clickable link from
  every other step's StepNav for the current project (`stepHref` appends `project_id`),
  so a user mid-workflow genuinely lands on `/step1?project_id=<real-id>` and sees a
  blank "new project" form — not a rare edge case.

Confirmed a real, already-existing fix path: `app/api/projects.py:129-137` has
`PUT /api/projects/{project_id}` → `project_service.update_project()`, accepting a
`ProjectUpdate` partial-patch model (`app/models/project.py:165-183`: `name`, `topic`,
`cefr_level`, `duration_minutes`, `num_speakers`, `genre`, `accent`,
`language_features`, `speakers` — every field Step 1's form collects). Its docstring
says "also used as the auto-save endpoint," but **no frontend code calls it today**
(`grep updateProject` across `frontend/` returns nothing) and `frontend/static/js/api.js`
has no wrapper for it yet — this task adds the first consumer.

## Objective

Fix both bugs using only real, already-existing backend capability — no new endpoints,
no invented regeneration/cascade logic.

### Required decisions (already settled by PM, do not re-litigate)

1. **Continue button — extend the existing status→step mapping, don't replace its
   logic.** The existing 2 cases (`draft`, `script_generated` → `/step2`) both resume to
   *the step that owns/produced that status* (draft has no script yet, so step 2 is
   where you'd make one; script_generated's script was made on step 2, so you land back
   there to review/regenerate it) — keep that pattern for the new cases rather than
   inventing a "next step" heuristic:
   - `audio_generated` → `/step4` (Audio — where that audio was generated)
   - `video_generated` → `/step5` (Video — where that video was generated)
   - `complete` → `/step7` (YouTube — the last step; defensive, currently unreachable)
   - Keep `draft`/`script_generated` → `/step2` exactly as-is.
   - Implement as a single `STATUS_TO_STEP` lookup object, not a growing if-chain.
   - If a project somehow has a status outside this map (defensive — should not happen
     given the enum), do nothing rather than throwing, matching today's silent-no-op
     safety envelope for unknown values — but this should not be reachable for any of
     the 5 known statuses after the fix, so do not treat it as a normal case.

2. **Config page — branch on whether `project_id` is present and resolve via a real
   fetch, don't guess from the URL alone.**
   - On `init()`, if `project_id` is present in the URL: call `Api.getProject(project_id)`
     (existing endpoint, `app/api/projects.py:120-126`, already returns full project incl.
     speakers).
     - If the fetch fails (bad/deleted id): show the existing error banner pattern
       ("We couldn't load this project.") — do not silently fall back to the blank
       create-form, since that's the exact bug being fixed.
     - If `project.status === "draft"`: **prefill the form** with the fetched values
       (name, topic, cefr, duration, genre, accent, language_features, speakers) and on
       submit call the new `Api.updateProject(project_id, patch)` (add this wrapper to
       `api.js`, mirroring the existing `request()` helper and the `PUT` pattern already
       used at `api.js:47`/`api.js:92`) instead of `createProject`. This is safe because
       nothing downstream has been generated yet from this config.
     - If `project.status !== "draft"` (script/audio/video already exist): render the
       form **read-only/disabled** (all inputs `disabled`, no submit button, or submit
       button removed) with a clear banner explaining configuration is locked because
       downstream content already depends on it, and that changing it here would not
       regenerate anything. **Do not** wire up silent full-rewrite semantics for
       already-progressed projects — that's a new feature (cascade/regenerate) this task
       does not add, consistent with "no fake features."
   - If `project_id` is absent (the existing "start a new project" entry point from the
     dashboard's "+ New Project" button): behave exactly as today — blank form,
     `createProject` on submit. Do not change this path at all.

## Proposed File-Level Plan

- `frontend/static/js/dashboard.js`: replace the `if` in the `continue` action handler
  with a `STATUS_TO_STEP` map lookup + `window.location.href` build, reusing the
  existing `encodeURIComponent(id)` pattern.
- `frontend/static/js/api.js`: add `updateProject: (id, patch) => request(\`/api/projects/${id}\`, { method: "PUT", body: JSON.stringify(patch) })` next to the existing `getProject`/`createProject`.
- `frontend/static/js/step1_config.js`: in `init()`, branch on `project_id` presence;
  add a fetch-and-prefill path + a read-only-lock render path; change `handleSubmit` to
  call `updateProject` when editing an existing draft project, `createProject` when not.
- `frontend/pages/step1_config.html`: only if a read-only banner element / disabled-state
  styling needs a new element — keep to the minimum, reuse existing `.error-banner` /
  `.card` classes if they already fit.
- New or extended browser test file (Codex to name and confirm in the pre-code plan,
  e.g. `tests/test_dashboard_continue_browser.py` and an extension to whichever existing
  file covers `/step1` — check for one first, e.g. `tests/test_step1_config_browser.py`
  or equivalent, before assuming it doesn't exist).

## Allowed files
- `frontend/static/js/dashboard.js`
- `frontend/static/js/api.js`
- `frontend/static/js/step1_config.js`
- `frontend/pages/step1_config.html` (only if strictly needed per above)
- Whatever existing or new browser test file(s) cover `/step1` and the dashboard —
  Codex to confirm exact filenames in the pre-code plan before touching any test file
  not listed here.
- This task card (`task-4.4.md`) for plan/evidence updates.

## Verification checklist
- [ ] Manual: dashboard with a project in each of the 5 statuses (seed via direct DB
  write or by walking a real project through the pipeline) — click Continue on each,
  confirm it lands on the mapped step and never no-ops.
- [ ] Manual: open Config (`/step1?project_id=<draft-project>`), confirm form is
  prefilled with the real values, edit one field, submit, confirm `Api.updateProject`
  was called (not `createProject`) and the same project id is preserved (no duplicate
  created) — verify via the dashboard project count before/after.
- [ ] Manual: open Config for a `script_generated`/`audio_generated`/`video_generated`
  project, confirm the form renders locked/read-only with no way to submit a change.
- [ ] Manual: open Config with no `project_id` (from "+ New Project"), confirm the
  blank-form + create-new-project path is completely unchanged.
- [ ] New/extended browser tests pass; full suite still 544+/544 (whatever the count is
  after this task's new tests) with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS files, `git diff --check` —
  all clean, real output pasted.
