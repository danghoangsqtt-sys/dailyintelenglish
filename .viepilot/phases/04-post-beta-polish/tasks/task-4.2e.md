# Task 4.2e: UI Redesign Slice 2 — YouTube Package page (`/step7`)

## Meta
- **ID**: 4.2e (fifth sub-task of Task 4.2 — UI Redesign Slice 2)
- **Phase**: 4
- **Status**: done (2026-09-16)
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

## PM Plan Review (2026-09-16) — APPROVED

Codex presented its pre-code plan per AR-06's 3-step process. PM independently
verified the plan's key technical claim before approving.

**Confirmed**: `frontend/pages/step7_youtube.html:115-160` really does nest the "Full
Package Export" section (`#export-status-note`/`#export-zip-link`) entirely inside
`#content-wrap`, and `step7_youtube.js`'s `render()` only calls `renderExportStatus()`
after the early-return checks for `state.packageLoadFailed`/`!state.package` — meaning
today, the static HTML text "Checking export readiness…" is never actually shown to a
user (it's hidden along with the whole `content-wrap` block until a package exists).
Codex correctly identified that moving Export into the always-visible inspector would
make this previously-invisible placeholder text visible and misleading whenever no
package exists yet, and proposed the minimal correct fix: change only the static HTML
default text to something honest ("Generate the YouTube package to check export
readiness"), relying on the existing `renderExportStatus()` to overwrite it with the
real ready/not-ready state once a package exists — no new JS branch, no new state, no
new API call. This is exactly right and exactly the kind of thing PM asked Codex to
flag rather than guess past.

Also confirmed the 3 specific test names Codex cited in its verification command
(`test_step7_no_overflow_at_1024`, `test_step7_ctrl_enter_triggers_generate_when_panel_visible`,
`test_step7_ctrl_enter_does_nothing_when_panel_hidden`) all exist exactly as named in
`tests/test_responsive_layout_browser.py`/`tests/test_keyboard_shortcuts_browser.py`.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step7_youtube.js`
- `tests/test_step_nav_browser.py`
- `tests/test_youtube_shell_browser.py` (new)
- `tests/test_youtube_browser.py` — confirmed **not** touched (Codex's baseline check
  found all 8 existing tests use stable ids, unaffected by the relocation)
- This task card, for evidence only (Status field remains PM-only)

**Plan approved as presented — no changes requested.** Codex may proceed to
implementation.

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

## Implementer Evidence (Awaiting PM Review — 2026-09-16)

Implementation is ready for PM review. Implementer did not change the task Status and
did not commit or push.

### Implementation summary

- Migrated YouTube Package to the shared shell with workflow StepNav, resizable
  sidebar and inspector, and no timeline.
- Kept Generate, Title Options, Description, Chapters, Tags, and Regenerate in the
  stage. Moved the existing Full Package Export readiness panel into the inspector.
- Preserved every existing element id and all generate/regenerate/copy/readiness logic.
  The only page-JS changes are the workflow StepNav variant and
  `WorkspaceShell.init()`.
- Did not add selection state, click handlers, or an inspector detail view to the three
  title cards.
- Changed only the export note's static initial HTML copy to the honest
  “Generate the YouTube package to check export readiness.” Since the export panel is
  now always visible, this replaces the old “Checking…” text that `render()` never
  updates while no package exists. Existing `renderExportStatus()` takes over after a
  package loads or is generated.
- Added real-Chromium coverage for shell structure, absence of a timeline, both pane
  resizers, sidebar collapse/re-expand, Generate populating all four stage sections,
  not-ready export gating, and ready export URL wiring.
- Applied only the pre-authorized Step 7 tuple/comment change in
  `tests/test_step_nav_browser.py`. All eight existing YouTube browser tests remain
  unchanged.

### Visual browser verification

Used the real local app and real Chromium at an explicit 1440×900 viewport with
deterministic API interception, matching the browser suite.

- Not-ready state: inspector note named both missing prerequisites, export link had
  `aria-disabled="true"`, all four content sections remained in the stage, and the
  page had no horizontal document overflow.
- Ready state: inspector note changed to Ready, export link had
  `aria-disabled="false"` with the real project export URL, and the long download label
  stayed inside the default 340px inspector without clipping or overflow.
- Temporary screenshots outside the repository (to respect `allowed_files`):
  - `C:\Users\Admin\AppData\Local\Temp\daily-intel-english-task-4.2e-not-ready.png`
  - `C:\Users\Admin\AppData\Local\Temp\daily-intel-english-task-4.2e-ready.png`

### Targeted browser verification

The first targeted run caught a test-authoring mismatch only: `getAttribute("href")`
returns the relative `/api/...` value, while the new assertion expected an absolute
localhost URL. The assertion was corrected to the exact relative URL; production code
was unchanged. The full targeted set then passed.

`venv\Scripts\python.exe -m pytest tests/test_youtube_shell_browser.py tests/test_youtube_browser.py tests/test_step_nav_browser.py tests/test_responsive_layout_browser.py::test_step7_no_overflow_at_1024 tests/test_keyboard_shortcuts_browser.py::test_step7_ctrl_enter_triggers_generate_when_panel_visible tests/test_keyboard_shortcuts_browser.py::test_step7_ctrl_enter_does_nothing_when_panel_hidden -q` (exit code 0):

```text
............................                                             [100%]
28 passed in 40.39s
```

### Required verification output

`venv\Scripts\python.exe -m pytest tests/ -q` (exit code 0):

```text
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 76%]
........................................................................ [ 89%]
..........................................................               [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
562 passed, 2 warnings in 281.02s (0:04:41)
```

`venv\Scripts\python.exe -m ruff check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/step7_youtube.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/04-post-beta-polish/tasks/task-4.2e.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step7_youtube.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step7_youtube.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_step_nav_browser.py', LF will be replaced by CRLF the next time Git touches it
```

The `git diff --check` messages are Windows line-ending conversion notices, not
whitespace errors.

## PM Re-review (2026-09-16) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for both touched files plus the new test
file:
- `step7_youtube.js`: exactly the 2 approved additions (`variant: "workflow"`,
  `WorkspaceShell.init()` matching the other 4 shell pages' exact shape) — zero other
  lines changed.
- `step7_youtube.html`: confirmed the "Full Package Export" section
  (`#export-status-note`/`#export-zip-link`) is now a standalone, always-visible
  `<section class="card export-card">` inside `#pane-inspector`, structurally outside
  `#content-wrap` — exactly the approved design. Confirmed the static initial text was
  changed to exactly "Generate the YouTube package to check export readiness." as
  agreed at plan review. Confirmed every other required element id survives unrenamed
  (`#error-banner`, `#project-name`, `#project-badges`, `#generate-panel`,
  `#generate-btn`, `#content-wrap`, `#title-grid`, `#description-text`,
  `#chapters-text`, `#chapters-estimate-note`, `#tags-list`, `#tags-text`,
  `#regenerate-btn`). CSS custom-property renames are the same verified pre-existing
  `style.css` aliases as 4.2d. No title-card selection state or click-to-inspect
  interaction was added — confirmed by absence in the diff.
- `tests/test_step_nav_browser.py`: exactly the pre-authorized one-line change.

**New test file review**: `test_youtube_shell_resizes_toggles_and_generate_populates_stage`
directly asserts the initial honest export text, confirms `#pane-timeline`/
`#resizer-top` don't exist, exercises both resizers and sidebar collapse with real
mouse/DOM events, then generates a package and confirms all 4 stage sections populate
while export correctly stays disabled with a status message naming both missing
prerequisites. `test_ready_export_stays_in_inspector_with_all_content_in_stage` loads
directly into the ready state and confirms the export link's exact real URL and
enabled state. Both tests directly exercise the one non-obvious risk this task carried
(the static-text fix) rather than just asserting structure.

**PM independently re-ran every verification command**: 28/28 targeted+regression
pass, `ruff check` clean, `node --check` clean, `git diff --check` exit 0 — all
matched the Implementer's report exactly.

**PM's own independent script** (mocked API routes directly against the real backend
contract, not reusing the Implementer's test file), beyond what was asked:
- First verified against the actual backend (`app/api/youtube.py:49-56`) that
  `GET .../youtube` returns `200` with `data: null` when no package exists yet — not a
  404 as PM's own first draft mock incorrectly assumed — confirming Codex's test
  mocks (which used `200`/`null`) accurately model the real API contract, not just a
  convenient fiction.
- Confirmed keyboard-driven resize on `#resizer-right` works (340px → 460px).
- Confirmed the inspector correctly hides below the shared shell's 1050px breakpoint
  (out of scope, unchanged, still works).

**Full suite, run independently**: 561 passed, 1 failed
(`test_generate_script_retries_on_429_then_succeeds`) in 1147.57s — the known
Gemini-retry timing flake class, confirmed passing in isolation at 0.71s. The
19-minute run time (vs. the ~250-450s baseline) is consistent with the documented
pattern that slow full-suite runs (system load) trigger this flake; Task 4.2e touched
zero backend/Gemini code. Non-regressive.

**Zero real defects found on PM review this round.** Accepted as delivered — no
changes requested.

**This closes Task 4.2e.** 5 of 7 Task 4.2 pages now use the shell conventions
(Learning, TTS, Video, Thumbnail, YouTube — plus Script from Task 2.4, which set the
original pattern but isn't counted in Task 4.2's own 7-page split). Remaining in Task
4.2's split: Music Library and Step1-Config, both deliberately NOT shell-based per the
2026-09-14 session decision.
