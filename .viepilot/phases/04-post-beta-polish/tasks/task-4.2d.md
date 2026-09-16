# Task 4.2d: UI Redesign Slice 2 — Thumbnail Generator page (`/step6`)

## Meta
- **ID**: 4.2d (fourth sub-task of Task 4.2 — UI Redesign Slice 2, resuming after
  Task 4.4's P0 bug fixes closed)
- **Phase**: 4
- **Status**: done (2026-09-16)
- **Priority**: medium
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Precedent: `tasks/task-4.2a.md` (Learning, `/step3`) is the closer reference for this
page than 4.2b/4.2c — Thumbnail has **no timeline** (confirmed decision, same as
Learning: no real "sequential items" concept, per the 2026-09-14 UI-redesign session).
Read `task-4.2a.md` first for the shell-without-timeline shape, then read this card in
full before touching anything — this page has one important difference from every
prior sub-task, called out below.

## Current state (researched before writing this plan — do not re-derive from scratch)

`frontend/pages/step6_thumbnail.html` + `frontend/static/js/step6_thumbnail.js` today: a
single-column page with 3 numbered sections — (1) **Choose a template**
(`#template-gallery`, a grid of template cards + `#variant-count` select +
`#generate-btn`), (2) **Select a favorite** (`#variant-grid`, generated A/B thumbnail
variants, click to favorite via `Api.selectThumbnailFavorite()`), (3) **Edit, preview,
and download** (`#editor-layout`: a live preview image + `#aspect-toggle` (16:9/9:16) on
the left, a "Manual editor" card on the right — `#headline-input`, 4 color pickers
(`#color-primary/secondary/accent/text`), `#save-status`, `#save-btn`,
`#retry-save-btn`, and a `#download-grid` with PNG/JPG links for both aspect ratios).

**Important, different from every prior Task 4.2 sub-task**: this page already has a
**real, live write-path editor** for the selected item, not a read-only inspector. The
"Manual editor" (section 3) is a genuine autosaving form — `handleEditorInput()` →
`scheduleSave()` (400ms debounce) → `runSave()` → `Api.editThumbnail()`, with real
conflict handling (409 stale-revision detection sets `state.staleConflict` and swaps
the Retry button to "Reload latest"), a real trailing-save-coalescing pattern (a save
that lands while a newer edit queued re-runs itself — `hasNewerDraft` check in
`runSave()`), a mounted `SaveIndicator`, and a `beforeunload` guard
(`hasUnresolvedEdit()`). None of this is being invented — it all exists today and must
be preserved exactly. Do not treat the inspector on this page as read-only just
because Learning's and Video's were.

Full function map in `step6_thumbnail.js` (do not modify JS logic, only what's needed
to keep it wired to relocated DOM — see Objective): `applyLocks`, `renderHeader`,
`renderTemplates`, `renderVariants`, `updateEditorAssets`, `syncEditorFromActive`,
`selectFavorite`, `setGenerateLoading`, `generateThumbnails`, `scheduleSave`,
`handleEditorInput`, `runSave`, `init`.

## Objective

Wrap in the shell, **no timeline**: `pane-sidebar` (StepNav, `variant: "workflow"`,
`currentStep: 6` — **the exact regression every one of 4.2a/4.2b/4.2c hit when this was
missing on their pages; this is now the 4th shell page, there is no excuse to repeat
it**) + `pane-main` (`pane-stage` only, no `pane-timeline`/`#resizer-top`) +
`pane-inspector`. Reuse `frontend/static/js/shell.js`'s `WorkspaceShell.init()` exactly
as the other 3 shell pages do (Learning/TTS/Video) — do not modify `shell.js` itself.

### Required decisions (already settled, do not re-litigate)

1. **`pane-stage` hosts sections 1 and 2** (template gallery + generate controls, and
   the variant grid) — this is the "browse and select" area, matching the same
   stage/inspector split every other shell page uses (stage = list/browse,
   inspector = selected-item detail).
2. **`pane-inspector` hosts section 3 in full** (preview image, aspect toggle, headline
   input, color palette, save-status/save-btn/retry-btn, download grid) — this is a
   **real editable inspector**, the one exception to every prior page's read-only
   inspector, because this page's per-item editing was already real, pre-existing
   functionality (unlike Learning's per-item actions, which don't exist in the
   backend, or Video's, which were deliberately kept read-only). Relocating it into
   the inspector pane is not adding a new write path — it already existed.
3. **Preserve every existing element id** referenced by `step6_thumbnail.js` exactly:
   `#workspace`, `#loading-panel`, `#error-banner`, `#project-name`, `#project-badges`,
   `#template-gallery`, `#variant-count`, `#generate-btn`, `#variant-grid`,
   `#variant-empty`, `#editor-placeholder`, `#editor-layout`, `#preview-image`,
   `#aspect-toggle` (+ its `[data-aspect]` buttons), `#headline-input`, the 4
   `[data-color]` inputs, `#save-status`, `#save-btn`, `#retry-save-btn`,
   `#download-grid` (+ its 4 `#download-{aspect}-{format}` links), `#save-indicator`.
   Do not rename any of them — the JS file should not need any logic changes, only the
   HTML structure around these ids changing (moving them into the new pane layout) and
   `init()`'s `StepNav.render()` call gaining `variant: "workflow"`.
4. **No timeline, no `Api.getScript()` or any new API call** — this page adds zero new
   backend calls, unlike Task 4.2c's Video page. Purely a layout/CSS change plus the
   one-line StepNav fix.

## Proposed File-Level Plan

- `frontend/pages/step6_thumbnail.html`: restructure into the shell skeleton
  (`#pane-sidebar` / `#pane-main` with `#pane-stage` only / `#pane-inspector`), moving
  sections 1+2 into the stage and section 3 into the inspector, trimming `<style>` to
  only page-specific classes still in use (most of the existing CSS should still apply,
  just reparented). Keep `<link>`/`<script>` tags as-is except adding `shell.js`.
- `frontend/static/js/step6_thumbnail.js`: add `variant: "workflow"` to the existing
  `StepNav.render()` call in `init()`'s `DOMContentLoaded` handler; add
  `WorkspaceShell.init({...})` (stage + inspector, no timeline/resizerTop) alongside
  the existing init logic. No other logic change expected — flag in the plan if one
  turns out to be necessary and why.
- `tests/test_step_nav_browser.py`: pre-authorized one-line extension,
  `if current_step in (2, 3, 4, 5):` → `if current_step in (2, 3, 4, 5, 6):` (same
  fix class as every prior sub-task).
- `tests/test_thumbnail_browser.py` and/or a new shell-specific test file — Codex to
  confirm in the pre-code plan whether the existing 6 tests in
  `tests/test_thumbnail_browser.py` (double-submit lock, favorite/preview/download +
  reload persistence, save-serialization, failed-save retry, stale-revision conflict,
  beforeunload guard) still pass unmodified against the new DOM layout, or need
  selector updates because an element moved between panes — report which, do not
  assume.

## Allowed files
- `frontend/pages/step6_thumbnail.html`
- `frontend/static/js/step6_thumbnail.js`
- `tests/test_step_nav_browser.py`
- `tests/test_thumbnail_browser.py`
- A new shell-specific browser test file, if Codex's plan proposes one (name to be
  confirmed in the pre-code plan, following the `test_{page}_shell_browser.py`
  convention from 4.2a/4.2c)
- This task card, for plan/evidence updates.

## PM Plan Review (2026-09-16) — APPROVED

Codex presented its pre-code plan per AR-06's 3-step process. PM independently
verified the 2 technical claims the plan's risk section rests on before approving:
- **Confirmed**: `frontend/static/css/style.css:225` really does
  `@media (max-width: 1050px) { .pane-inspector, #resizer-right { display: none; } }`
  — Codex's claim that the shared shell already hides the inspector below 1050px
  (out of scope, not this task's concern) is accurate.
- **Confirmed**: `frontend/static/js/shell.js:87` really does clamp the inspector
  resizer to `min: 260, max: 480`, and the `collapseBtn` wiring (line 89-93) only ever
  targets `sidebar` — there is genuinely no inspector-collapse API today. Codex's test
  plan (resize both panes, collapse/re-expand sidebar only) correctly matches what the
  shared shell actually supports, not an invented capability.

**One open risk PM is tracking, not blocking approval on**: relocating the "Manual
editor" (live preview + editing form) into a 260-480px inspector is a real width
reduction from its current ~1.45fr two-column layout, and a thumbnail's whole purpose
is visual judgment — a preview that becomes too small to actually evaluate would be a
real regression even if every test passes. This was already decided in the task card
("required decision, do not re-litigate") before this narrower-than-expected width was
concretely understood, so PM is not asking Codex to re-litigate the stage/inspector
split now. Instead: **please include a real screenshot of the relocated preview in the
evidence** (not just a passing test) so PM can judge legibility during review. If it
turns out to be too small to be useful, that becomes a fast, scoped follow-up
(e.g., a page-specific override to the inspector's default/max width) — not a reason to
redo this task now.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/pages/step6_thumbnail.html`
- `frontend/static/js/step6_thumbnail.js`
- `tests/test_step_nav_browser.py`
- `tests/test_thumbnail_shell_browser.py` (new)
- `tests/test_thumbnail_browser.py` — confirmed **not** touched (Codex's baseline check
  found all 6 existing tests use stable ids unaffected by the relocation)
- This task card, for evidence only (Status field remains PM-only)

**Plan approved as presented — no changes requested.** Codex may proceed to
implementation.

## Verification checklist
- [ ] All 6 existing `tests/test_thumbnail_browser.py` tests still pass (updated
  selectors if needed, but the same real behaviors — double-submit lock, favorite
  selection, save debounce/coalescing, 409 conflict handling, beforeunload guard —
  must all still be genuinely exercised, not weakened).
- [ ] Manual/automated check: generate 3+ variants, select a favorite, edit the
  headline and a color, confirm the debounced autosave fires once and the preview
  updates — the inspector's write path must work exactly as before, just relocated.
- [ ] Resizer collapse/expand (sidebar + inspector) works, matching Learning/TTS/Video.
- [ ] `StepNav` shows `variant: "workflow"` styling identical to the other 3 shell
  pages at `currentStep: 6`.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake class
  is the only acceptable non-deterministic failure, and only if it reproduces as a pass
  in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS, `git diff --check` — all
  clean, real output pasted.

## Implementer Evidence (Awaiting PM Review — 2026-09-16)

Implementation is ready for PM review. Implementer did not change the task Status and
did not commit or push.

### Implementation summary

- Migrated Thumbnail Generator to the shared shell with workflow StepNav, resizable
  sidebar and inspector, and no timeline.
- Kept template generation and variant selection in the stage. Moved the complete
  existing editor — rendered preview, aspect toggle, headline, palette, save/retry,
  and downloads — into the inspector without changing its API or save-state logic.
- Preserved the 400 ms debounce, trailing-save coalescing, stale-revision conflict,
  SaveIndicator, and beforeunload paths. The only page-JS changes are the workflow
  StepNav variant and `WorkspaceShell.init()`.
- Added real-Chromium coverage for shell structure, absence of a timeline, both pane
  resizers, sidebar collapse/re-expand, generate-three, favorite selection, a combined
  headline/color edit producing exactly one debounced PATCH, and preview revision
  refresh.
- Applied only the pre-authorized Step 6 tuple/comment change in
  `tests/test_step_nav_browser.py`. The six existing thumbnail state-machine browser
  tests remain unchanged.

### Visual browser verification and screenshot

Used the real local app, real Chromium, and the real Step 6 frontend at an explicit
1440×900 viewport. API responses were deterministically intercepted as in the browser
suite; the preview image itself was a real 1280×720 repository static asset.

- The default inspector measured 340×842 px.
- Its preview frame measured 281×180 px; the 1280×720 image rendered at approximately
  279×157 px, retaining its full 16:9 composition without cropping.
- Edited the headline and accent color immediately before capture. Exactly one PATCH
  fired and the screenshot shows the updated headline, saved state, selected variant,
  workflow sidebar, stage, preview, palette, and download controls together.
- Screenshot evidence is intentionally outside the repository to respect `allowed_files`:
  `C:\Users\Admin\AppData\Local\Temp\daily-intel-english-task-4.2d-preview.png`.

### Targeted browser verification

`venv\Scripts\python.exe -m pytest tests/test_thumbnail_shell_browser.py tests/test_thumbnail_browser.py tests/test_step_nav_browser.py tests/test_save_indicator_browser.py tests/test_responsive_layout_browser.py -q` (exit code 0):

```text
..................................                                       [100%]
34 passed in 62.51s (0:01:02)
```

### Required verification output

`venv\Scripts\python.exe -m pytest tests/ -q` (exit code 0):

```text
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
........................................................                 [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
560 passed, 2 warnings in 274.32s (0:04:34)
```

`venv\Scripts\python.exe -m ruff check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/step6_thumbnail.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/04-post-beta-polish/tasks/task-4.2d.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step6_thumbnail.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step6_thumbnail.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_step_nav_browser.py', LF will be replaced by CRLF the next time Git touches it
```

The `git diff --check` messages are Windows line-ending conversion notices, not
whitespace errors.

## PM Re-review (2026-09-16) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 3 touched files plus the new test
file:
- `step6_thumbnail.js`: exactly the 2 approved additions (`variant: "workflow"` on
  `StepNav.render()`, a `WorkspaceShell.init()` call matching Learning's exact
  shape/keys) — zero other lines changed, confirmed no save/debounce/conflict logic
  was touched.
- `step6_thumbnail.html`: every element id the task card required to survive is
  present and unrenamed (`#workspace`, `#loading-panel`, `#error-banner`,
  `#project-name`, `#project-badges`, `#template-gallery`, `#variant-count`,
  `#generate-btn`, `#variant-grid`, `#variant-empty`, `#editor-placeholder`,
  `#editor-layout`, `#preview-image`, `#aspect-toggle` + buttons, `#headline-input`,
  the 4 `[data-color]` inputs, `#save-status`, `#save-btn`, `#retry-save-btn`,
  `#download-grid` + its 4 links, `#save-indicator`) — checked one by one against the
  diff. The CSS custom-property renames (`--text-muted`→`--muted`,
  `--surface-border`→`--border`, `--bg-elevated`→`--surface-2`,
  `--surface-border-hover`→`--border-strong`) were verified as true aliases already
  defined side-by-side in `style.css`'s `:root` (both light and dark blocks) — not a
  functional change, just switching to the shorter names `style.css`'s own shared
  component rules already use. New classes used in the rewritten header/shell markup
  (`.brand`, `.brand-mark`, `.project-name`, `.shell-flex`, `.shell-row`,
  `.sidebar-collapse-btn`, `.stage-header`, `.stage-title`, `.stage-actions`) all
  confirmed to already exist in the shared `style.css` — nothing invented. The
  "Thumbnail workspace" sidebar summary block is a verified line-for-line copy of
  Learning's equivalent block (`step3_learning.html`), consistent with precedent, not
  a new pattern.
- `tests/test_step_nav_browser.py`: exactly the pre-authorized one-line change.

**New test file review**: `test_thumbnail_shell_structure_resizes_and_sidebar_toggles`
asserts stage/inspector separation, confirms `#pane-timeline`/`#resizer-top` genuinely
don't exist (`count() == 0`, not just untested), drags both resizers with real mouse
events, and toggles sidebar collapse with `aria-expanded` checks both directions.
`test_generated_favorite_editor_autosaves_once_inside_inspector` edits headline and an
accent color within the same debounce window and asserts exactly 1 `PATCH` fired with
the combined payload (including the pre-existing `.toUpperCase()` hex-normalization
still applying), plus confirms the preview image's `src` reflects the new revision —
directly proving the relocated editor's write path still works end-to-end.

**PM independently re-ran every verification command**: 34/34 targeted+regression
pass, `ruff check` clean, `node --check` clean, `git diff --check` exit 0 — all
matched the Implementer's report exactly.

**PM's own independent script + screenshots** (mocked API routes directly, a
different project id from the Implementer's test file), beyond what was asked:
- Confirmed keyboard-driven resize on `#resizer-right` (focus + repeated `ArrowLeft`)
  works, growing the inspector from 340px to 460px — the shared shell's keyboard
  accessibility (flagged as a general polish gap for the *timeline* resizer in the
  2026-09-16 Codex UI audit) is present and functional on this page's sidebar/inspector
  resizers.
- Screenshots in both themes (dark and light) confirm clean rendering, no overflow, no
  unstyled elements, and the relocated preview stays visually usable at both the
  default 340px and expanded 460px inspector widths — resolving the tracked "preview
  too small" risk from plan review satisfactorily; no follow-up needed now.

**Full suite, run independently**: 560 passed, 0 failed, 244.89s — zero flakes,
consistent with the Implementer's own clean 560/560 run. Up from 558 (this task's 2
new tests).

**Zero real defects found on PM review this round.** Accepted as delivered — no
changes requested.

**This closes Task 4.2d.** 4 of 7 pages now use the shell conventions (Script,
Learning, TTS, Video, Thumbnail). Remaining: YouTube, Music Library, Step1-Config.
