# Task 5.3: Small polish batch

## Meta
- **ID**: 5.3 (third and final task of Phase 5 — UI Polish Backlog)
- **Phase**: 5
- **Status**: done (2026-09-17)
- **Priority**: low (small, low-risk polish items, bundled per the 2026-09-16
  brainstorm session's decision — see `docs/brainstorm/session-2026-09-16.md`)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: 3 of the 2026-09-16 Codex UI audit's remaining P2 findings, bundled into one
task per the brainstorm session's decision (mirrors Task 2.3's and Task 4.4's
precedent of bundling related small items rather than one task per finding). All 3
re-verified as still real by PM before opening this task.

## Current state (researched before writing this plan — do not re-derive from scratch)

### Item 1 — Learning card keyboard accessibility
`frontend/static/js/step3_learning.js`: item cards are plain
`<div class="card item-card" data-section="..." data-index="...">` (built in
`vocabItemHtml`/similarly-named functions for idioms/grammar/questions, lines
~110-160) — no `role`, no `tabindex`. Selection is click-only, handled by
`handleTabPanelClick(e)` (line 244-249, delegated on `contentWrap`):
`e.target.closest(".item-card")` → reads `dataset.section`/`dataset.index` →
`selectItem(section, index)`. A keyboard-only user cannot focus or activate a card
today. Confirmed via direct read — matches the audit finding exactly.

### Item 2 — Learning inspector default state
`state.selectedItem` starts `null` (line 20) and stays `null` until a card is
clicked. `renderInspector()` (line 204-213) shows a plain "Select an item to inspect
it." placeholder whenever nothing is selected — including right after a pack first
loads or is (re)generated, when the 340px inspector pane sits empty despite real data
already being on screen. `state.activeTab` defaults to `"vocabulary"`
(`TAB_SECTION.vocabulary === "vocabulary"`, line 7 and 19). `render()` (line 251-272)
is the central function called after both initial load and generate/regenerate,
ending in `renderAllTabs()`.

### Item 3 — Video avatar section always expanded
`frontend/pages/step5_video.html:121-129`: "1. Speaker avatars (optional)" is the
**first** section shown in the workspace, always expanded, above "2. Choose a
background" — the section already honestly discloses
"Lip-sync video isn't built yet — these images aren't used by 'Generate video'
below," but its prominent, always-open placement ahead of the actually-functional
steps is what the audit flagged as unnecessary cognitive load. Precedent for
collapsing optional content already exists in this codebase:
`frontend/static/js/step2_script.js:134-141` uses a plain
`<details class="notes-details"><summary>Language notes</summary>...</details>` for
each line's optional language notes — no custom JS toggle needed, native
`<details>`/`<summary>` handles expand/collapse (and keyboard activation) for free.

## Objective

Three independent, low-risk fixes — no shared code path between them, safe to review
and verify as one batch but each individually simple to reason about.

### Required decisions (already settled by PM, do not re-litigate)

1. **Learning cards**: add `role="button"` and `tabindex="0"` to each `.item-card`,
   and a `keydown` handler (on the same delegated `contentWrap`, alongside
   `handleTabPanelClick`) that calls `selectItem()` on `Enter` or `Space` — `Space`
   must call `event.preventDefault()` to stop the page from scrolling, matching how a
   real `<button>` behaves. Do not convert the cards to real `<button>` elements —
   they contain other interactive children (inline-editable `.field` elements per
   `commitField()`), and nesting interactive elements inside a `<button>` is invalid
   HTML; `role="button"` + `tabindex` + keydown is the correct pattern here, same as
   ARIA authoring practices for a composite widget.
2. **Learning inspector default item**: in `render()`, after a pack exists and tabs
   are rendered, if `state.selectedItem` is still `null`, auto-select the first item
   of the **currently active tab's section** (`state.activeTab` defaults to
   `"vocabulary"`) — i.e. index `0` of `state.pack[TAB_SECTION[state.activeTab]]`, if
   that array is non-empty. **Never override an existing selection** — this only
   fires when nothing is selected yet (first load, first generate, or after
   `switchTab()` clears a stale cross-tab selection at line 287-289 — that existing
   clear-on-tab-switch behavior should also gain the same "select the new tab's first
   item" default, for consistency, rather than leaving the inspector empty again).
3. **Video avatar section**: wrap the existing "1. Speaker avatars (optional)"
   section in a native `<details>`/`<summary>` (collapsed by default, i.e. no `open`
   attribute), mirroring the exact pattern already used for Script's language notes.
   Do not build a custom JS-driven collapse/expand — the native element already
   handles keyboard activation and state for free. Keep the existing honest
   disclosure text inside; do not soften or remove it.

## Proposed File-Level Plan

- `frontend/static/js/step3_learning.js`: add `role="button"` + `tabindex="0"` to the
  4 item-card template functions; add a `keydown` listener (delegated on
  `contentWrap`, alongside the existing click listener) for `Enter`/`Space`; add the
  "select first item of the active tab if nothing selected" call in `render()` and in
  `switchTab()`'s existing clear-on-switch branch.
- `frontend/pages/step5_video.html`: wrap the "1. Speaker avatars (optional)" section
  in `<details><summary>...</summary>...</details>`, collapsed by default.
- `frontend/static/css/style.css` or a page-local style — only if genuinely needed to
  style the `<summary>` consistently with the rest of the page (check how Script's
  `.notes-details`/`.notes-body` are styled first, reuse if it fits) — state whether
  needed.
- New or extended browser test coverage — Codex to confirm exact file(s) in the
  pre-code plan. Must include: a real keyboard-only selection test for a Learning
  card (Tab to focus, Enter or Space to select, inspector updates), a test confirming
  the inspector shows the first vocabulary item immediately after a pack loads/
  generates without any click, and a test confirming the Video avatar section is
  collapsed on page load (and that its content is still reachable/expandable).

## Allowed files
- `frontend/static/js/step3_learning.js`
- `frontend/pages/step5_video.html`
- `frontend/static/css/style.css` (only if needed per above — state whether it was
  needed in the evidence)
- Existing or new browser test file(s) — Codex to confirm exact filename(s) in the
  pre-code plan (e.g. extending `tests/test_learning_shell_browser.py` and/or
  `tests/test_video_shell_browser.py`).
- This task card, for plan/evidence updates.

## PM Plan Review (2026-09-17) — APPROVED

Codex presented its pre-code plan per AR-06's 3-step process. Plan matches every
required decision in this task card, with two well-reasoned refinements PM verified
before accepting.

**Refinement 1 — event-target guard on the new keydown handler**: the plan gates the
new Enter/Space handler on `event.target === card` (not just `.closest(".item-card")`
like the existing click handler), specifically to avoid hijacking Enter/Space already
handled by nested interactive children — the inline-edit `.field`s' own
`handleContentKeydown` and the real `<button>` "Show Answer" toggle. Correct and
necessary: without this guard, pressing Enter while editing a field or pressing Space
on the toggle button would incorrectly also trigger card selection.

**Refinement 2 — did not reuse `.notes-details` for the avatar section**: PM
independently checked `frontend/static/css/style.css:175-178` and confirmed Codex's
reasoning is accurate — `.notes-details` is styled at `font-size: 13px` with a muted
`summary` color, clearly designed for small inline per-line content (Script's
language notes), not a page-level section heading. Keeping `.section-title` on the
`<summary>` with new minimal page-local CSS in `step5_video.html` is the right call,
not corner-cutting.

**Test file choice confirmed reasonable**: extending `tests/test_video_studio_
browser.py` (which already owns the real avatar upload/preview/remove flow tests)
rather than `test_video_shell_browser.py` makes sense — those existing tests need to
open the now-collapsed `<details>` before continuing their existing interactions, so
the natural home for that fix is alongside the tests it fixes forward-compatibility
for. Explicitly disclosed which old assertions need updating (previously-open avatar
controls, previously-empty inspector) rather than silently changing them.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/static/js/step3_learning.js`
- `frontend/pages/step5_video.html`
- `tests/test_learning_shell_browser.py`
- `tests/test_video_studio_browser.py`
- This task card, for evidence only (Status field remains PM-only)

**Plan approved as presented. No changes requested.** Codex may proceed to
implementation.

## PM Scope Extension (2026-09-17) — `tests/test_video_shell_browser.py` authorized

Mid-implementation, Codex correctly stopped and reported rather than silently
patching a file outside `allowed_files`: the pre-existing
`test_avatar_and_generate_flows_remain_wired` test in
`tests/test_video_shell_browser.py` (from Task 4.2c, not originally in this task's
locked file list) uploads an avatar and waits for `.avatar-preview` to become
*visible* — now failing because that element lives inside the newly-collapsed
`#avatar-details` and stays hidden until expanded. This is a real, correctly-diagnosed
consequence of Task 5.3's own intentional behavior change, not an unrelated issue.

**Authorized**: a minimal, narrow fix to `tests/test_video_shell_browser.py` —
open `#avatar-details` right after the workspace loads, before the existing
upload/remove flow continues. No assertion, production logic, or scope beyond that
one narrow fix is authorized. `tests/test_video_shell_browser.py` is added to
`allowed_files` for this specific change only.

## Verification checklist
- [ ] A Learning card can be reached via `Tab` and activated via `Enter` and via
  `Space`, updating the inspector each time — a real keyboard-driven test, not just
  an attribute-presence check.
- [ ] The Learning inspector shows the first vocabulary item immediately after the
  pack first loads/generates, with no click needed — and switching tabs shows that
  tab's first item, not an empty state.
- [ ] An existing selection is never silently overridden by the default-select logic
  (e.g., selecting item #3, then re-triggering `render()`, should not jump back to
  item #1).
- [ ] The Video avatar section is collapsed on page load; expanding it still shows
  the existing upload/remove functionality working exactly as before.
- [ ] Existing Learning and Video shell tests still pass unmodified or with justified
  updates.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS, `git diff --check` — all
  clean, real output pasted.

## Implementer Evidence (Awaiting PM Review — 2026-09-17)

### Scope delivered

- All four Learning `.item-card` templates now expose `role="button"` and
  `tabindex="0"`. A delegated handler activates only the card that is itself the
  event target on Enter/Space, so nested inline editors and the real Show Answer
  button keep their existing keyboard behavior. Space prevents its scrolling default.
- Learning selects item 0 from the active tab only when no selection exists. This
  applies after loading or generating a pack and after a cross-tab selection is
  cleared; a real existing selection is retained.
- Video's existing avatar section is now a native, initially-collapsed `<details>`
  with a `<summary>`. All disclosure copy, element ids, upload/preview/remove behavior,
  and API paths remain unchanged.
- `frontend/static/css/style.css` was not needed and was not changed. The two visual
  rules specific to the page-level avatar summary live in `step5_video.html`.
- The PM-authorized extension to `tests/test_video_shell_browser.py` is exactly one
  line opening `#avatar-details` before its existing upload/remove flow; no assertion
  in that file was changed.

### Browser verification

`venv\Scripts\python.exe -m pytest tests/test_learning_shell_browser.py tests/test_video_studio_browser.py tests/test_video_shell_browser.py -q`
(exit code 0):

```text
....................                                                     [100%]
20 passed in 42.82s
```

`venv\Scripts\python.exe -m pytest tests/test_ui_async_browser.py tests/test_responsive_layout_browser.py tests/test_step_nav_browser.py -q`
(exit code 0):

```text
.............................                                            [100%]
29 passed in 61.72s (0:01:01)
```

A separate disposable Chromium run at 1440×900 verified the actual focus/keyboard
path, inspector contents, scroll behavior, native details state, retained disclosure,
and document overflow. Raw output:

```json
{"learning_initial_contains": true, "tab_focused_index": "1", "enter_selected_second": true, "space_selected_first": true, "space_scroll_unchanged": true, "avatar_open_before": false, "avatar_open_after_enter": true, "disclosure_preserved": true, "horizontal_overflow": false, "screenshot": "C:\\Users\\Admin\\AppData\\Local\\Temp\\task-5.3-video-avatar-details.png"}
```

The screenshot was kept outside the repository at
`C:\Users\Admin\AppData\Local\Temp\task-5.3-video-avatar-details.png`. Visual review
confirmed the expanded native section fits the existing shell without horizontal
overflow.

### Required verification output

`venv\Scripts\python.exe -m pytest tests/ -q` (exit code 1 — two occurrences of the
task card's accepted pre-existing Gemini-retry/shared-sleep timing flake; both pass
together in isolation immediately below):

```text
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 37%]
........................................................................ [ 50%]
....................................................FF.................. [ 63%]
........................................................................ [ 75%]
........................................................................ [ 88%]
...................................................................      [100%]
================================== FAILURES ===================================
______________ test_generate_script_backoff_sequence_is_1s_2s_4s ______________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000024F7C6E4DE0>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_script_backoff_sequence_is_1s_2s_4s(monkeypatch, no_real_sleep):
        queue_responses(
            monkeypatch,
            [
                FakeResponse(429, text="rate limited"),
                FakeResponse(429, text="rate limited"),
                FakeResponse(429, text="rate limited"),
                gemini_ok_response(VALID_LINES),
            ],
        )

        await script_service.generate_script("proj-1", SAMPLE_CONFIG)

>       assert no_real_sleep == [1.0, 2.0, 4.0]
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0, 2.0, 4.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 5038962 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_script_service.py:145: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=3 retry_in_s=4.0
_______ test_generate_script_exhausts_one_model_then_falls_back_to_next _______

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x0000024F7C8D4A60>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_script_exhausts_one_model_then_falls_back_to_next(monkeypatch, no_real_sleep):
        """After 4 failed attempts on the primary model, the next fallback model is tried."""
        calls = queue_responses(
            monkeypatch,
            [FakeResponse(429, text="rate limited")] * 4 + [gemini_ok_response(VALID_LINES)],
        )

        lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)

        assert len(lines) == 2
        assert calls["n"] == 5
        assert calls["models"] == [script_service.GEMINI_MODEL_FALLBACKS[0]] * 4 + [
            script_service.GEMINI_MODEL_FALLBACKS[1]
        ]
>       assert no_real_sleep == [1.0, 2.0, 4.0]  # backoff resets per model, but only 1 model exhausted here
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0, 2.0, 4.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 5651650 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_script_service.py:162: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.script_service:script_service.py:122 gemini_retryable_error model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.script_service:script_service.py:159 gemini_model_exhausted model=gemini-3.8-flash prompt_hash=56199050ed00c89c status=429 — trying next fallback model
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s
FAILED tests/test_script_service.py::test_generate_script_exhausts_one_model_then_falls_back_to_next
2 failed, 569 passed, 2 warnings in 1217.99s (0:20:17)
```

Task 5.3 changes no Python/backend/Gemini code. The failures contain 5,038,962 and
5,651,650 unrelated 0.1-second entries respectively in the globally patched
`no_real_sleep` fixture — the documented resource-load-sensitive flake class.
Immediate isolated rerun together:

`venv\Scripts\python.exe -m pytest tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s tests/test_script_service.py::test_generate_script_exhausts_one_model_then_falls_back_to_next -q`
(exit code 0):

```text
..                                                                       [100%]
2 passed in 0.69s
```

`venv\Scripts\ruff.exe check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/step3_learning.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --exit-code -- frontend/static/css/style.css` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/05-ui-polish-backlog/tasks/task-5.3.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step5_video.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step3_learning.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_learning_shell_browser.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_video_shell_browser.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_video_studio_browser.py', LF will be replaced by CRLF the next time Git touches it
```

These are Windows line-ending conversion notices, not whitespace errors.

## PM Re-review (2026-09-17) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 5 touched files:
- `step3_learning.js`: `role="button"`/`tabindex="0"` added to all 4 item-card
  templates. `selectFirstActiveItem()` is a clean, well-guarded helper (no-op if
  already selected or pack absent); both `render()` and `switchTab()` were refactored
  to `if (!selectFirstActiveItem()) renderInspector();`, correctly handling every
  case traced by hand: switching to a genuinely different tab clears the stale
  selection then defaults to the new tab's first item; re-activating the tab that
  already owns the current selection leaves it untouched (the helper's own guard
  short-circuits); an empty target section correctly falls back to the placeholder.
  `handleItemCardKeydown()` correctly gates on `e.target === card` (not just
  `.closest()`), isolating it from the inline-edit fields' own keydown handler and
  the real "Show Answer" button's native activation — confirmed this can't
  double-fire since a card is never simultaneously a `.field` element.
- `step5_video.html`: exactly the `<section>`→`<details>`/`<h2>`→`<summary>` swap,
  no `open` attribute, 2 minimal page-local CSS rules, all existing content/ids
  preserved verbatim.
- `tests/test_video_shell_browser.py`: exactly the one authorized line
  (`#avatar-details summary` click before the existing flow) — no assertion changed.
- `tests/test_video_studio_browser.py`: confirmed the added assertions directly test
  the collapse/expand behavior itself (`element.open` false→true, `#avatar-grid`
  hidden→visible via real keyboard activation) before continuing the pre-existing
  upload/remove flow unchanged — a genuine improvement, not just a passing-test fix.
- `style.css`: confirmed untouched via `git diff --exit-code`.

**New/renamed test review**: `test_learning_shell_browser.py`'s renamed test
specifically exercises the exact edge case this task's decisions were built around —
re-activating the *same* tab does not reset a real selection back to item 0 (asserts
"deliberate" — the item-1 content — survives a same-tab reactivation), while
switching to a genuinely different tab does default to that tab's first item, and the
quiz tab now shows an answer with no click at all. A second new test covers the
fresh-generate path distinctly. A third new test does a real keyboard walkthrough
(Tab order from an inline-edit field into the next card, Enter selecting it, Tab
order from the last tab button into the first card, and an actual `event.defaultPrevented`
capture confirming Space's `preventDefault()` really fired, not just inferred from
the visible outcome).

**PM independently re-ran every verification command**: 20/20 targeted, 29/29
regression, `ruff check` clean, `node --check` clean, `style.css` confirmed
untouched, `git diff --check` exit 0 — all matched the Implementer's report exactly.

**Screenshot review**: confirms the avatar `<details>` expands correctly via
keyboard with a visible focus outline, layout clean, no overflow.

**Full suite, run independently**: 571 passed, 0 failed, 324.96s — a clean run with
no flakes at all this time, faster than the Implementer's own 1217.99s run (which hit
the known Gemini-retry flake twice, both confirmed passing in isolation).

**Zero real defects found on PM review.** Accepted as delivered — no changes
requested.

**This closes Task 5.3 — and Phase 5 (UI Polish Backlog) in full.** All 3 tasks done:
5.1 Dashboard pagination, 5.2 Timeline polish, 5.3 Small polish batch.
