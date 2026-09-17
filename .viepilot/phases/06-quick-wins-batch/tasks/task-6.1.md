# Task 6.1: Quick wins batch — theme flash, dead-end error link, range slider styling

## Meta
- **ID**: 6.1 (first task of Phase 6 — Quick Wins Batch)
- **Phase**: 6
- **Status**: in_progress (2026-09-17)
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
