# Task 2.6: Fix 3 findings from the post-Task-2.5 audit pass

## Meta
- **ID**: 2.6 (new scope, born from a `/vp-audit` pass requested before Phase 3)
- **Phase**: 2
- **Status**: done
- **Priority**: medium (1 real data-consistency bug, 1 real unsafe-escaping bug, 1 docs fix)
- **Assignee**: PM (Claude Code)

## Doc-First Gate

User ran `/vp-audit` after Task 2.5 and asked to fix the real findings before moving to
Phase 3. 3 of the 6 findings were selected to fix now (the other 3 are pre-existing,
low-severity, noted only): ARCHITECTURE.md doc drift, `mp4_path_vertical` orphaning on
regenerate, and `escapeHtml()` unsafe for HTML-attribute-value contexts.

## Objective

### 2.6a — ARCHITECTURE.md doc drift (Tier 2)
Update the two stale API doc lines under `### Video` to mention `aspect_ratio` and the
`mp4_vertical` download format, matching what Task 2.5b actually shipped.

### 2.6b — `mp4_path_vertical` orphaning on regenerate (Tier 3, real bug)
`video_service.generate_video()`: when a regenerate call does NOT request `"9:16"` but a
previous vertical render exists on disk from an earlier call, the old
`video_vertical.mp4` is now stale (derived from a 16:9 render/subtitle-burn that no
longer matches the fresh one just produced) — delete it from disk so the DB's `NULL`
for `mp4_path_vertical` is accurate (no orphaned file misleadingly lingering), rather
than just relying on the DB write to silently disconnect a still-downloadable-by-direct-
path but now-mismatched file.

### 2.6c — `escapeHtml()` unsafe for attribute-value contexts (Tier 3, real bug)
`frontend/static/js/step1_config.js::escapeHtml()`: extend to also escape `"` and `'`
(the DOM `textContent`→`innerHTML` trick already escapes `&`/`<`/`>` but leaves quotes
untouched, since they have no special meaning in text-node content — only in
attribute-value content). Makes the helper genuinely safe for both of its real call
sites: `value="${escapeHtml(speaker.name)}"` (pre-existing, real user input) and the two
new `title="${escapeHtml(note)}"` tooltip sites from Task 2.5c.

## Allowed files

- `.viepilot/phases/02-testing-polish/tasks/task-2.6.md` (this file)
- `.viepilot/ARCHITECTURE.md`
- `app/services/video_service.py`
- `frontend/static/js/step1_config.js`
- `tests/test_video_service.py`
- New: `tests/test_step1_escape_html_browser.py` (real regression coverage — a speaker
  name / accent note containing `"` must not break out of its attribute)
- `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`,
  `.viepilot/phases/02-testing-polish/PHASE-STATE.md`, `.viepilot/HANDOFF.json` (state
  updates on completion)

## Verification

1. `pytest tests/test_video_service.py -q`
2. `pytest tests/test_step1_escape_html_browser.py -q`
3. `pytest tests/ -q`
4. `node --check frontend/static/js/step1_config.js`
5. `ruff check app/ tests/`
6. `git diff --check`
7. `git status --short`

## Implementer Evidence (PM-verified 2026-09-14)

### 2.6a — ARCHITECTURE.md
Updated the two stale `### Video` API doc lines to mention `aspect_ratio` (request body)
and `mp4_vertical` (download format), matching what Task 2.5b actually shipped.

### 2.6b — Orphaned `mp4_path_vertical` on regenerate
`generate_video()`: when `aspect_ratio != "9:16"`, now deletes any stale
`video_vertical.mp4` left over from an earlier `"9:16"` call for the same project
(`Path.unlink(missing_ok=True)` off the event loop via `asyncio.to_thread`). New
`test_generate_video_16x9_regenerate_deletes_stale_vertical_file`: generates with
`"9:16"` first (confirms the file exists), regenerates with the default `"16:9"`, and
asserts the old file is actually gone from disk, not just dropped from the DB row.

### 2.6c — `escapeHtml()` unsafe for attribute contexts
Extended to also replace `"` → `&quot;` and `'` → `&#39;` after the existing
`textContent`→`innerHTML` escaping (which only ever covered `&`/`<`/`>`). **Verified the
fix is real, not just plausible**: reverted the change, re-ran the new
`tests/test_step1_escape_html_browser.py`, and watched it fail for a genuine reason — a
speaker name containing `"><img src=x onerror="...">` broke out of the rendered
`value="..."` attribute (`input_value()` came back empty instead of the injected
string, proving the HTML parser actually split the attribute early). Restored the fix,
re-ran — passes. A second test confirms the Task 2.5c Scottish tooltip (quote-free)
still renders its exact original text after the escaping change.

### Full verification
1. `pytest tests/test_video_service.py -q` → **13 passed**.
2. `pytest tests/test_step1_escape_html_browser.py -q` → **2 passed**.
3. `pytest tests/ -q` → **532 passed, 1 failed, 672.08s**. The 1 failure
   (`test_learning_service.py::test_generate_learning_pack_exhausts_one_model_then_falls_back`)
   is the pre-existing tracked Gemini-retry timing flake (TRACKER.md Known Issues) —
   Task 2.6 touched zero Gemini/learning_service code. Re-ran in isolation:
   **1 passed in 0.59s**, confirming the flake, not a regression.
4. `node --check frontend/static/js/step1_config.js` → exit 0.
5. `ruff check app/ tests/` → **All checks passed!**
6. `git diff --check` → clean (only benign LF→CRLF autocrlf warnings).
7. `git status --short` → change set matches `Allowed files` exactly.

## PM Acceptance

**ACCEPTED 2026-09-14.** All 3 findings selected by the user fixed and real-verified
(one with an explicit revert-and-confirm-failure step, since it's a security-adjacent
fix). Zero regressions. The other 3 audit findings (missing `die-vp-p1-complete` tag,
pre-existing error-path field-wiping in `save_video_job`, single-statement assumption in
`init_db()`'s migration fallback) remain noted-only in TRACKER.md Known Issues, per the
user's explicit choice not to act on them now.
