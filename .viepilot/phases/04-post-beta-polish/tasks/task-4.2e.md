# Task 4.2e: UI Redesign Slice 2 — YouTube Package page (`/step7`)

## Meta
- **ID**: 4.2e (fifth sub-task of Task 4.2 — UI Redesign Slice 2)
- **Phase**: 4
- **Status**: in_progress (2026-09-16)
- **Priority**: medium
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Precedent: `tasks/task-4.2d.md` (Thumbnail, `/step6`) is the closest reference —
same "shell, no timeline" shape, same "preserve every element id, no logic change"
discipline, same pattern of flagging a real design question up front rather than
guessing. Read it first. This page has its **own** real design question, different
from Thumbnail's — see "Required decisions" below, do not assume the stage/inspector
split copies Thumbnail's 1:1.

## Current state (researched before writing this plan — do not re-derive from scratch)

`frontend/pages/step7_youtube.html` + `frontend/static/js/step7_youtube.js` today: a
single-column page, one `#generate-panel` (shown until a package exists) or
`#content-wrap` (5 sequential sections once generated) — **Title Options**
(`#title-grid`: 3 fixed cards, click-worthy/educational/seo, each showing its full
text + a copy button — no selection state, all 3 always shown at once), **Description**
(`#description-text` + copy), **Chapters** (`#chapters-text` + an honest
measured-vs-estimated note + copy), **Tags** (`#tags-list` chips + copy), **Full
Package Export** (`#export-status-note` + `#export-zip-link`, a real readiness check —
`state.videoReady` from `Api.getVideoStatus()`, `state.thumbnailReady` from
`Api.listThumbnails()`, both already-fetched in `init()`, no new API calls needed), and
a `#regenerate-btn` (confirm-gated, overwrites everything).

**Important, different from every prior Task 4.2 sub-task**: this page has **no
per-item selection concept at all** — unlike Learning's cards, TTS/Video's script
lines, or Thumbnail's variant grid, nothing here is "click one of several things to see
its detail." The whole generated package (titles, description, chapters, tags) is
already fully displayed at once, all the time. There is no natural "selected item" to
put in an inspector the way every prior sub-task had one.

Full function map in `step7_youtube.js` (do not modify JS logic, only what's needed to
keep it wired to relocated DOM — see Objective): `renderHeader`, `renderTitles`,
`renderTags`, `render`, `renderExportStatus`, `setGenerateLoading`, `handleGenerate`,
`handleRegenerate`, `handleCopyClick`, `init`.

## Objective

Wrap in the shell, **no timeline**: `pane-sidebar` (StepNav, `variant: "workflow"`,
`currentStep: 7` — **the exact regression every one of 4.2a/4.2b/4.2c/4.2d hit when
this was missing; this is now the 5th shell page**) + `pane-main` (`pane-stage` only)
+ `pane-inspector`. Reuse `frontend/static/js/shell.js`'s `WorkspaceShell.init()`
exactly as the other 4 shell pages do — do not modify `shell.js` itself.

### Required decisions (already settled, do not re-litigate)

1. **`pane-stage` hosts Title Options, Description, Chapters, and Tags** (the 4
   generated-content sections, plus `#generate-panel` and the Regenerate action) — this
   is the primary, always-fully-visible content, with no per-item selection state to
   split out.
2. **`pane-inspector` hosts the "Full Package Export" section** (`#export-status-note`,
   `#export-zip-link`). This is a deliberate departure from Thumbnail/Learning/TTS/
   Video's pattern of "inspector = detail of the selected item" — there is no selected
   item on this page. Instead, Export Readiness is chosen because it is the one section
   that already behaves like a persistent **workflow-status panel** (real dynamic
   state: ready/not-ready + exactly what's missing, computed from
   `state.videoReady`/`state.thumbnailReady`), which is a natural fit for an
   always-visible side panel — closer in spirit to how the shared sidebar's small
   "workspace summary" card works on Learning/Thumbnail, except this one has real
   backend-driven state rather than static copy. **Do not invent a per-title-variant
   click-to-inspect interaction** (e.g., a title-character-count view) — the 3 title
   cards have no additional data beyond what's already shown on each card, and adding
   one would be a new feature this structural-only task does not authorize.
3. **Preserve every existing element id** referenced by `step7_youtube.js` exactly:
   `#error-banner`, `#project-name`, `#project-badges`, `#generate-panel`,
   `#generate-btn`, `#content-wrap`, `#title-grid` (+ its per-variant
   `#title-text-{variant}` ids, dynamically generated — the container id is what
   matters here), `#description-text`, `#chapters-text`, `#chapters-estimate-note`,
   `#tags-list`, `#tags-text`, `#export-status-note`, `#export-zip-link`,
   `#regenerate-btn`. Do not rename any of them — the JS file should not need any logic
   changes, only the HTML structure around these ids changing (moving them into the new
   pane layout, `#export-status-note`/`#export-zip-link` specifically into the
   inspector) and `init()`'s `StepNav.render()` call gaining `variant: "workflow"`.
4. **No timeline, no new API call** — this page already fetches everything it needs in
   `init()` (`Api.getProject`, `Api.getYoutubePackage`, `Api.getVideoStatus`,
   `Api.listThumbnails`); purely a layout/CSS change plus the one-line StepNav fix.

## Proposed File-Level Plan

- `frontend/pages/step7_youtube.html`: restructure into the shell skeleton
  (`#pane-sidebar` / `#pane-main` with `#pane-stage` only / `#pane-inspector`), moving
  the generate panel + Title/Description/Chapters/Tags sections + Regenerate button
  into the stage, and the Full Package Export section into the inspector. Trim
  `<style>` to only page-specific classes still in use, reusing shared shell classes
  (`.topbar`, `.brand`, `.shell-flex`, `.shell-row`, `.pane-sidebar`, `.pane-stage`,
  `.pane-inspector`, `.stage-header`, `.stage-title`, etc. — confirmed already defined
  in `style.css` from Task 4.2d's review) rather than reinventing local topbar/layout
  CSS, matching the precedent Task 4.2d set. Keep `<link>`/`<script>` tags as-is except
  adding `shell.js`.
- `frontend/static/js/step7_youtube.js`: add `variant: "workflow"` to the existing
  `StepNav.render()` call in `init()`'s `DOMContentLoaded` handler; add
  `WorkspaceShell.init({...})` (stage + inspector, no timeline/resizerTop). No other
  logic change expected — flag in the plan if one turns out to be necessary and why.
- `tests/test_step_nav_browser.py`: pre-authorized one-line extension,
  `if current_step in (2, 3, 4, 5, 6):` → `if current_step in (2, 3, 4, 5, 6, 7):`
  (same fix class as every prior sub-task).
- `tests/test_youtube_browser.py` (8 existing tests) — Codex to confirm in the pre-code
  plan whether these still pass unmodified against the new DOM layout, or need selector
  updates because an element moved between panes — report which, do not assume.

## Allowed files
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step7_youtube.js`
- `tests/test_step_nav_browser.py`
- `tests/test_youtube_browser.py`
- A new shell-specific browser test file, if Codex's plan proposes one (name to be
  confirmed in the pre-code plan, following the `test_{page}_shell_browser.py`
  convention from 4.2a/4.2c/4.2d)
- This task card, for plan/evidence updates.

## Verification checklist
- [ ] All 8 existing `tests/test_youtube_browser.py` tests still pass (updated
  selectors if needed, but the same real behaviors — generate/regenerate confirm gate,
  copy-to-clipboard, export-readiness gating, measured-vs-estimated chapters note —
  must all still be genuinely exercised, not weakened).
- [ ] Manual/automated check: generate a package, confirm all 4 stage sections render,
  confirm the inspector's export-readiness note and download link update correctly for
  both the "not ready" and "ready" states (video + thumbnail present).
- [ ] Resizer collapse/expand (sidebar + inspector) works, matching the other 4 shell
  pages.
- [ ] `StepNav` shows `variant: "workflow"` styling identical to the other 4 shell
  pages at `currentStep: 7`.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake class
  is the only acceptable non-deterministic failure, and only if it reproduces as a pass
  in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS, `git diff --check` — all
  clean, real output pasted.
