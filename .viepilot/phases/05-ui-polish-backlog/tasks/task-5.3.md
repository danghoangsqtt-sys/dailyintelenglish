# Task 5.3: Small polish batch

## Meta
- **ID**: 5.3 (third and final task of Phase 5 — UI Polish Backlog)
- **Phase**: 5
- **Status**: in_progress (2026-09-17)
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
