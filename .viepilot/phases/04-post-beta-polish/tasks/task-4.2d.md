# Task 4.2d: UI Redesign Slice 2 — Thumbnail Generator page (`/step6`)

## Meta
- **ID**: 4.2d (fourth sub-task of Task 4.2 — UI Redesign Slice 2, resuming after
  Task 4.4's P0 bug fixes closed)
- **Phase**: 4
- **Status**: in_progress (2026-09-16)
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
