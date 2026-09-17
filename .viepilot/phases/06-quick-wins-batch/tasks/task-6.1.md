# Task 6.1: Quick wins batch — theme flash, dead-end error link, range slider styling

## Meta
- **ID**: 6.1 (first task of Phase 6 — Quick Wins Batch)
- **Phase**: 6
- **Status**: done (2026-09-17)
- **Priority**: medium (real, verified, low-risk fixes — bundled per precedent)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: a user-commissioned independent deep-dive audit from Gemini
(`C:\Users\Admin\Documents\audit_chuyensau_dailyintelenglish`, 2026-09-17) found 8
issues beyond the original Codex audit's scope. PM independently verified 4 of them
before scoping this task — **1 turned out to be a false positive**, corrected below,
not carried into this task. The 3 real, verified findings are bundled here per the
same precedent as Task 2.3/4.4/5.3 (bundle related small items rather than one task
per finding).

## Current state (researched before writing this plan — do not re-derive from scratch)

### Item 1 — Theme flash on 4 pages (verified real)
`music_library.html`, `step1_config.html`, `step6_thumbnail.html`,
`step7_youtube.html` all hardcode `<html lang="en" data-theme="dark">` (confirmed via
`grep -c 'data-theme="dark"' frontend/pages/*.html` — exactly these 4, count 1 each;
`dashboard.html`/`step2-5` have 0). `frontend/static/js/theme.js`: `Theme.init()` runs
on `DOMContentLoaded` (line 35) and correctly defaults to `"light"` when no
`localStorage` preference exists (`localStorage.getItem(STORAGE_KEY) || "light"`,
matching the project's light-by-default decision from Task 2.4). Since
`DOMContentLoaded` fires *after* the browser has already parsed and painted the
hardcoded `data-theme="dark"` attribute, any user without a stored dark preference
sees a real dark→light flash navigating to these 4 pages. Fix: remove the hardcoded
`data-theme="dark"` from these 4 files' `<html>` tag — `Theme.init()` already applies
the correct theme on load, the same as the other 5 pages that never had this
attribute at all.

### Item 2 — No-project-id dead-end error (verified real)
`step2_script.js`, `step3_learning.js`, `step4_tts.js`, `step5_video.js`,
`step6_thumbnail.js`, `step7_youtube.js` each independently call
`showError("Missing project. Please start from the Dashboard.")` when
`project_id` is absent from the URL. Each page's own `showError(message)` function
(e.g. `step2_script.js:37-42`) sets `banner.textContent = message` — plain text only,
confirmed via `grep 'showError(\`|showError(.*+|showError(.*\${'` returning zero
matches across all files (every `showError` call site passes a static, hardcoded
string, never interpolated/dynamic content) — meaning it's safe to add a real link
here without any XSS risk, since nothing about these call sites is attacker-influenced.

### Item 3 — Range slider default styling (verified real)
`step4_tts.html:46`: `.slider-row input[type="range"] { flex: 1; }` is the only rule
touching these inputs — no thumb/track color styling at all, so browsers render their
own default appearance (e.g. Chrome's blue), inconsistent with the app's purple
accent design system. `frontend/static/js/step4_tts.js`'s `buildSlider()` (line
153-177) creates each `<input type="range">` inside a `.slider-row` — the existing
selector already used in the CSS, no JS changes needed for a pure color-styling fix.

### Corrected finding — YouTube chapters (NOT included, verified false positive)
Gemini's report claimed YouTube chapter timestamps "always use a fixed 150 WPM
estimate instead of real audio timestamps." **This is incorrect** — PM traced the
actual code path: `app/services/youtube_service.py::generate_package()` (line
214-277) already branches correctly — `real_chapters_from_timestamps()` (line
191-211) uses real measured `start_sec` values whenever `timestamps` is passed, and
`app/api/youtube.py:42-43` already fetches the real completed audio job and passes
its timestamps whenever one exists. `chapters_estimated` is correctly `False` in that
case. The word-count `estimate_chapters()` fallback only runs when no audio exists
yet — the honest, intended behavior (matches this page's own existing UI disclosure:
"✅ Measured from the final generated audio." vs "⏱ Estimated..."). The only genuinely
stale thing is a docstring comment inside `estimate_chapters()` itself ("blocked on
ffmpeg" — historically true, no longer accurate since ffmpeg was installed
2026-09-12) — a one-line comment tidy, not worth its own task, **not included here**.

## Objective

Three independent, low-risk, verified fixes — no shared code path between them.

### Required decisions (already settled by PM, do not re-litigate)

1. **Theme flash**: simply remove `data-theme="dark"` from the 4 files' `<html>` tag
   (matching `dashboard.html`/`step2-5`'s existing attribute-free state exactly). No
   JS change needed or wanted — `theme.js` already does the right thing once it runs.
2. **Dead-end error link**: add a small, purpose-built function per page (e.g.
   `showMissingProjectError()`) that sets `banner.innerHTML` to a fixed, hardcoded
   string containing a real `<a href="/">← Go to Dashboard</a>` link — used **only**
   for this one specific message. **Do not** change the existing `showError(message)`
   function's `textContent`-only contract for any other call site — every other
   `showError` call in these files stays exactly as safe as it is today. This mirrors
   the project's own CR-05 discipline (never let dynamic/external content reach
   `innerHTML`) while safely covering this one 100%-static-string case.
3. **Range slider styling**: CSS-only, `.slider-row input[type="range"]` gains
   `accent-color: var(--accent)` (the simplest, most broadly-supported modern fix —
   check current target-browser support is acceptable; if a richer custom
   thumb/track look is wanted, `-webkit-appearance: none` + custom thumb rules are a
   fallback, but **do not** implement a dynamic fill-percentage indicator (would
   require new JS state to track `--pct` on every input event) — that's a nice-to-have
   beyond what the actual complaint (color mismatch) requires.

## Proposed File-Level Plan

- `frontend/pages/music_library.html`, `frontend/pages/step1_config.html`,
  `frontend/pages/step6_thumbnail.html`, `frontend/pages/step7_youtube.html`: remove
  `data-theme="dark"` from the `<html>` tag (1 line each).
- `frontend/static/js/step2_script.js`, `step3_learning.js`, `step4_tts.js`,
  `step5_video.js`, `step6_thumbnail.js`, `step7_youtube.js`: add a small
  `showMissingProjectError()`-style function; replace the "Missing project" call site
  in each with it. Every other `showError` call in these files stays unchanged.
- `frontend/pages/step4_tts.html`: add `accent-color` (or equivalent) styling to the
  existing `.slider-row input[type="range"]` rule.
- New or extended browser test coverage — Codex to confirm exact file(s) in the
  pre-code plan. Must include: a real check that the 4 pages' initial HTML has no
  `data-theme` attribute (not just that `theme.js` still applies one correctly after
  load — the whole point is what renders *before* JS runs), a real click-through test
  confirming the "Go to Dashboard" link navigates to `/` on at least one of the 6
  pages, and a check that clicking it doesn't error when other showError call sites
  still exist. Range slider color can be a lighter-touch visual/computed-style check.

## Allowed files
- `frontend/pages/music_library.html`
- `frontend/pages/step1_config.html`
- `frontend/pages/step6_thumbnail.html`
- `frontend/pages/step7_youtube.html`
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step2_script.js`
- `frontend/static/js/step3_learning.js`
- `frontend/static/js/step4_tts.js`
- `frontend/static/js/step5_video.js`
- `frontend/static/js/step6_thumbnail.js`
- `frontend/static/js/step7_youtube.js`
- Existing or new browser test file(s) — Codex to confirm exact filename(s) in the
  pre-code plan.
- This task card, for plan/evidence updates.

## PM Plan Review (2026-09-17) — APPROVED

Codex presented its pre-code plan per AR-06's 3-step process. Plan matches every
required decision in this task card exactly.

**Correctly self-identified the key methodological trap**: checking the post-JS DOM
state for `data-theme` absence would be wrong, since `theme.js` always sets *some*
value once it runs — the plan explicitly commits to checking the raw served HTML
(before any script executes), matching the whole point of this fix (what paints
*before* JS runs). Confirmed this is the right approach without needing to raise it.

**Six near-identical `showMissingProjectError()` helpers, deliberately not
refactored into a shared utility**: correct call — matches this project's established
precedent (e.g. Task 5.2 duplicating `measuredClipWidth()` across 2 files rather than
extracting a shared module) of keeping small per-page helpers local rather than
introducing new shared infrastructure for a 3-line function.

**Range slider**: exactly `accent-color: var(--accent)`, no JS/fill-percentage state
— matches the settled scope boundary precisely.

**Test plan**: the new `tests/test_quick_wins_browser.py` bundle is well-designed —
raw-HTML theme check, default+stored-preference across all 9 pages (a real
regression net, not just the 4 changed pages), missing-project link + real
click-through navigation on step2-7, and a control test proving a normal API error
still renders plain text with no link (directly verifying every other `showError`
call site's safety is untouched, not just asserted). Extending
`tests/test_tts_shell_browser.py` with a real *computed*-style check for
`accent-color` (not just confirming the CSS rule exists in source) is the right level
of rigor.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/pages/music_library.html`, `step1_config.html`, `step6_thumbnail.html`,
  `step7_youtube.html` (theme attribute only)
- `frontend/pages/step4_tts.html` (slider CSS only)
- `frontend/static/js/step2_script.js`, `step3_learning.js`, `step4_tts.js`,
  `step5_video.js`, `step6_thumbnail.js`, `step7_youtube.js` (new helper + one call
  site each)
- `tests/test_quick_wins_browser.py` (new)
- `tests/test_tts_shell_browser.py` (extended)
- This task card, for evidence only (Status field remains PM-only)

**Plan approved as presented. No changes requested.** Codex may proceed to
implementation.

## Verification checklist
- [ ] Each of the 4 affected pages' raw initial HTML (before any JS runs) has no
  `data-theme` attribute on `<html>` — a real check of the served markup, not just
  the post-JS DOM state.
- [ ] `theme.js` still correctly applies the user's stored/default theme on all 9
  pages — no regression to the existing (already-correct) 5 pages.
- [ ] The "Missing project" error state on at least one of the 6 pages shows a real,
  clickable "Go to Dashboard" link that navigates to `/`.
- [ ] Every other `showError` call site in these 6 files is confirmed unchanged
  (still plain-text, no new `innerHTML` exposure).
- [ ] The TTS speed/pitch/volume sliders visually use the accent color instead of the
  browser default.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS, `git diff --check` — all
  clean, real output pasted.

## Implementer Evidence (Codex, 2026-09-17)

### Implementation summary

- Removed the hardcoded `data-theme="dark"` attribute from the four approved HTML
  pages. No change was made to `theme.js`.
- Added one local `showMissingProjectError()` helper to each Step 2–7 script and
  routed only the missing-`project_id` branch through it. Each helper contains a
  fixed, non-interpolated Dashboard link; the existing `showError(message)`
  implementations and all their other call sites remain unchanged.
- Added `accent-color: var(--accent)` to the existing TTS range-input selector. No
  slider JavaScript or fill-percentage state was introduced.
- Added `tests/test_quick_wins_browser.py` with raw-response theme assertions,
  default/stored-theme coverage across all nine UI routes, missing-project coverage
  across Step 2–7, real Dashboard navigation, and a normal-error plain-text control.
- Extended `tests/test_tts_shell_browser.py` with a Chromium computed-style assertion
  comparing a real TTS slider's `accentColor` with the resolved `--accent` token.

### Targeted and regression browser tests

Command:

```text
venv\Scripts\python.exe -m pytest tests/test_quick_wins_browser.py tests/test_tts_shell_browser.py -q
```

Output:

```text
...................                                                      [100%]
19 passed in 27.82s
```

Command:

```text
venv\Scripts\python.exe -m pytest tests/test_step_nav_browser.py tests/test_responsive_layout_browser.py tests/test_keyboard_shortcuts_browser.py tests/test_new_shell_resize_browser.py tests/test_learning_shell_browser.py tests/test_video_shell_browser.py tests/test_thumbnail_shell_browser.py tests/test_youtube_shell_browser.py -q
```

Output:

```text
...............................................                          [100%]
47 passed in 72.15s (0:01:12)
```

### Full suite

Command:

```text
venv\Scripts\python.exe -m pytest tests/ -q
```

Output:

```text
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 61%]
........................................................................ [ 74%]
........................................................................ [ 86%]
........................................................................ [ 98%]
.......                                                                  [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
583 passed, 2 warnings in 417.85s (0:06:57)
```

### Ruff

Command:

```text
venv\Scripts\ruff.exe check app/ tests/
```

Output:

```text
All checks passed!
```

### JavaScript syntax

Commands:

```text
node --check frontend/static/js/step2_script.js
node --check frontend/static/js/step3_learning.js
node --check frontend/static/js/step4_tts.js
node --check frontend/static/js/step5_video.js
node --check frontend/static/js/step6_thumbnail.js
node --check frontend/static/js/step7_youtube.js
```

Output: no output; all six commands exited with code 0.

### Diff whitespace check

Command:

```text
git diff --check
```

Output (exit code 0; notices only, no whitespace errors):

```text
warning: in the working copy of '.viepilot/phases/06-quick-wins-batch/tasks/task-6.1.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/music_library.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step1_config.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step4_tts.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step6_thumbnail.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step7_youtube.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step2_script.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step3_learning.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step4_tts.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step5_video.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step6_thumbnail.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step7_youtube.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_tts_shell_browser.py', LF will be replaced by CRLF the next time Git touches it
```

### Scope confirmation

- Only the production files and two browser-test files locked in PM Plan Review were
  changed, plus this evidence section.
- No backend/API/schema, shared theme/shell code, project status, commit, or push was
  changed by the Implementer.

## PM Re-review (2026-09-17) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 13 touched files:
- The 4 theme-flash HTML files: each changed by exactly one line
  (`<html lang="en" data-theme="dark">` → `<html lang="en">`), byte-for-byte
  identical across all 4, nothing else touched.
- `step4_tts.html`: exactly `accent-color: var(--accent);` added to the existing
  `.slider-row input[type="range"]` rule, no other CSS changed.
- All 6 JS files: identical pattern confirmed across every one —
  `showMissingProjectError()` sets `banner.innerHTML` to a single-quoted, fully
  static string literal (`'Missing project. <a href="/">← Go to Dashboard</a>'`, no
  template interpolation anywhere), only the one "no project_id" call site replaced,
  the existing `showError(message)` function and every other call site confirmed
  untouched via direct diff read.
- Confirmed via `git diff --exit-code -- app/ frontend/static/js/theme.js
  frontend/static/css/style.css` (exit 0) that no backend, `theme.js`, or shared
  `style.css` was touched.

**New/extended test review**: `test_pages_do_not_ship_a_hardcoded_theme` correctly
uses `page.request.get()` — a real, direct HTTP fetch, not a browser navigation —
avoiding the exact methodological trap both the plan and PM had flagged (post-JS DOM
state always has *some* `data-theme` value once `theme.js` runs). The
default/stored-theme test parametrizes across all 9 routes and both preference
states, giving genuine regression coverage beyond just the 4 changed pages. The
missing-project tests use semantic `get_by_role("link", name=...)` locators and
include a real click-through to `/`. The negative-control test
(`test_regular_error_remains_plain_text_without_a_link`) mocks a real 500 error and
asserts zero `<a>` tags in the resulting banner — directly, empirically proving every
other `showError` call site's safety rather than just asserting it from the diff.
The TTS slider test uses a clever dynamic probe element to resolve `var(--accent)`
to its actual computed color in the current theme context, rather than hardcoding an
expected hex value that would break if the token's value ever changed.

**PM independently re-ran every verification command**: 19/19 targeted, 47/47
regression, `ruff check` clean, all 6 `node --check` clean, `git diff --check` exit
0 — all matched the Implementer's report exactly.

**Full suite, run independently**: 583 passed, 0 failed, 345.53s — a fully clean run
with zero flakes at all.

**Zero real defects found on PM review.** Accepted as delivered — no changes
requested.

**This closes Task 6.1 — and Phase 6 (Quick Wins Batch) in full**, since it was the
phase's only task.
