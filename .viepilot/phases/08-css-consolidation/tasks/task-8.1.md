# Task 8.1: Reconcile disabled-button CSS drift (ENH-005); ENH-004 re-scoped, not fixed

## Meta
- **ID**: 8.1 (first task of Phase 8 — CSS Consolidation)
- **Phase**: 8
- **Status**: done (2026-09-18)
- **Priority**: medium (verified cosmetic drift, low risk)
- **Assignee**: PM (Claude Code) — self-implemented per explicit user request
  ("để tiết kiệm thời gian bạn có thể tự xử lý luôn được không?", 2026-09-18), a
  one-time deviation from the AR-06 PM/Codex-Implementer split for this task only.
  PM still holds itself to the same doc-first plan, independent verification, and
  git-persistence gates as any Codex-implemented task.

## Doc-First Gate

Origin: `.viepilot/requests/ENH-004.md` and `.viepilot/requests/ENH-005.md`,
auto-logged by `/vp-audit` (2026-09-17). User asked to continue processing both.
Investigation before writing this plan changed the scope of both:

### ENH-004 — re-investigated, NOT fixed this task (see "ENH-004 finding" below)

### ENH-005 — investigated in full, real minimal fix identified

## Current state (researched before writing this plan)

### ENH-004 finding: the single connection is a deliberate, already-correct design — no small fix exists

`app/api/projects.py` lines 20-36 (an existing, detailed code comment PM had not
previously read closely enough) explain that the whole app already serializes
**every** route — reads included — on one connection-wide `asyncio.Lock`
(`_write_lock`), specifically *because* there is exactly one shared `aiosqlite`
connection and SQLite does not support nested transactions on a single connection.
This is not an accidental gap; it is the correct, already-reasoned solution to the
exact hazard a single connection creates (dirty reads / phantom reads / cross-request
rollback corruption).

Given this, adding `PRAGMA journal_mode=WAL` (the "recommended" fix in `ENH-004.md`)
would be **purely cosmetic and provide zero real benefit**: WAL's actual benefit
(readers not blocking on a writer) only manifests when readers and the writer use
*separate* connections. Since every request already funnels through the same one
connection serialized by `_write_lock` in Python, WAL would not relax that
serialization at all — it would only add `-wal`/`-shm` sidecar files and checkpoint
behavior for no measurable gain. A fix that actually changes the concurrency
characteristics here would require replacing `_write_lock` with a real connection-pool
architecture (one connection per request, careful per-route re-derivation of the
isolation guarantees the comment above documents) — a genuinely large architectural
change, not a quick win, and explicitly the kind of change this project has
consistently deferred for a solo local-use single-user app (Progress cancellation,
LivePortrait lip-sync, and now this).

**Decision**: do not implement anything for ENH-004 in this task. Correct
`.viepilot/requests/ENH-004.md` to record this finding (already-intentional design,
no low-risk fix available) rather than leaving it as an open "TODO: add WAL/pool".
Leave it explicitly deferred, same standing as Progress cancellation/LivePortrait.

### ENH-005 finding: real drift traced to one missing shared selector + 2 accidental overrides

The shared `frontend/static/css/style.css:102` rule is
`.btn[disabled] { cursor: not-allowed; opacity: .58; pointer-events: none; }` — it
has no `aria-disabled` variant. Several pages render an `<a class="btn ...">` styled
as a button (a real `<a>` cannot have a working native `disabled` attribute), and use
`aria-disabled="true"` instead — confirmed via `frontend/static/js/step6_thumbnail.js:101`
and `step7_youtube.js:125`, both call `link.setAttribute("aria-disabled", ...)` on a
`class="btn ..."` anchor (`#export-zip-link` in `step7_youtube.html:161`,
`.download-link` anchors in `step6_thumbnail.html`). Each page independently invented
a local fix for this real gap, and they drifted:
- `music_library.html:93`: `.btn:disabled { cursor: not-allowed; opacity: 0.55;
  transform: none; }` — targets a real `<button disabled>` (confirmed: every disabled
  element on this page — `deleteButton`, the upload `<input>` — either already has the
  `.btn` class or isn't styled as `.btn` at all, so this rule is fully redundant with
  the shared `.btn[disabled]` rule, just at the wrong opacity, and page-local rules
  win the cascade since they load after the shared stylesheet).
- `step7_youtube.html:75`: `.btn[aria-disabled="true"] { opacity: 0.55;
  pointer-events: none; }` — the real gap-filler, but wrong opacity, and now
  redundant once the shared rule is extended.
- `step6_thumbnail.html:108-112`: `.btn[disabled], button[disabled],
  a[aria-disabled="true"] { opacity: 0.55; cursor: not-allowed; pointer-events: none;
  }` — a 3-selector bundle. Confirmed via `step6_thumbnail.js:89` and `:123/:161`
  that `.template-option`/`.variant-card` are real bare `<button>` elements with
  **no** `.btn` class (`button.className = "card template-option"` /
  `"card variant-card"`) — so `button[disabled]` here is the one genuinely
  page-specific, non-redundant part of this rule and must be kept (just at the
  correct opacity). `.btn[disabled]` and `a[aria-disabled="true"]` become redundant
  once the shared rule is extended.
- `step6_thumbnail.html:216`: `.btn-sm { padding: 7px 11px; font-size: 12px;
  text-decoration: none; }` — `font-size: 12px` and `text-decoration: none` already
  match/are already inherited from the shared `.btn`/`.btn-sm` rules (`.btn` already
  sets `text-decoration: none` for every `.btn`-classed element); the only real
  divergence is `padding: 7px 11px` vs. the shared `.btn-sm`'s `padding: 5px 10px`
  (`style.css:99`) — no comment or functional reason found for the difference,
  confirmed accidental drift.

## Objective

Reconcile the disabled-button/`.btn-sm` visual drift to one consistent, shared
definition, removing now-redundant page-local CSS in the process — CSS-only, no JS
changes, no new behavior, matching the Task 6.1 precedent (CSS-only fixes, no
JS/architecture expansion beyond the verified complaint).

### Required decisions

1. Extend the shared `.btn[disabled]` rule in `style.css` to also match
   `.btn[aria-disabled="true"]`, at the existing shared values (opacity `.58`,
   `cursor: not-allowed`, `pointer-events: none`) — a single source of truth for
   every `.btn`-classed disabled element or disabled-styled link, everywhere.
2. Remove `music_library.html`'s and `step7_youtube.html`'s now-fully-redundant
   local overrides entirely.
3. In `step6_thumbnail.html`, keep only the genuinely non-redundant
   `button[disabled]` selector (for the bare `.template-option`/`.variant-card`
   buttons), corrected to the shared opacity value; drop `.btn[disabled]` and
   `a[aria-disabled="true"]` from that local rule since the shared rule now covers
   them.
4. Remove `step6_thumbnail.html`'s local `.btn-sm` override entirely — the shared
   `.btn-sm` padding (`5px 10px`) applies uniformly once it's gone.
5. Do not touch any JS file, any other CSS rule, or any other page's styling beyond
   what's listed above.

## Proposed File-Level Plan

- `frontend/static/css/style.css`: extend the `.btn[disabled]` selector list to
  include `.btn[aria-disabled="true"]` (1 line changed).
- `frontend/pages/music_library.html`: delete the local `.btn:disabled` rule (1 line
  removed).
- `frontend/pages/step7_youtube.html`: delete the local `.btn[aria-disabled="true"]`
  rule (1 line removed).
- `frontend/pages/step6_thumbnail.html`: simplify the local disabled-button rule to
  `button[disabled]` only, at the corrected opacity; delete the local `.btn-sm` rule
  entirely.
- New or extended browser test coverage in `tests/test_quick_wins_browser.py` (the
  file already covers Task 6.1's related theme/error-link "quick wins" — this is a
  natural extension, not a new file): a computed-style check proving a probe
  `.btn[disabled]` element and a probe `.btn[aria-disabled="true"]` element render
  the identical opacity on at least 2 of the affected pages (proving no more
  per-page drift, without hardcoding a literal opacity value — compare the two
  probes to each other, matching the Task 6.1 `accent-color` test's pattern), plus a
  check that a `.btn.btn-sm` probe on `step6_thumbnail.html` now renders the same
  computed padding as one on an unrelated page that never had a local override.
- `.viepilot/requests/ENH-004.md`: update with the re-scoped finding (no fix
  implemented; recorded as an intentional, already-correct design with no low-risk
  fix available).
- `.viepilot/requests/ENH-005.md`: mark done once implemented, with PM Acceptance
  evidence.

## Allowed files
- `frontend/static/css/style.css`
- `frontend/pages/music_library.html`
- `frontend/pages/step7_youtube.html`
- `frontend/pages/step6_thumbnail.html`
- `tests/test_quick_wins_browser.py`
- `.viepilot/requests/ENH-004.md`
- `.viepilot/requests/ENH-005.md`
- This task card, for plan/evidence updates.

## Verification checklist
- [ ] A real disabled `.btn` element and a real `.btn[aria-disabled="true"]` element
  render the same computed opacity on every affected page.
- [ ] `step6_thumbnail.html`'s bare `.template-option`/`.variant-card` buttons still
  render the correct disabled opacity (the one genuinely page-specific selector is
  preserved, just corrected).
- [ ] `step6_thumbnail.html`'s `.btn-sm` elements render the same computed padding as
  the shared `.btn-sm` rule elsewhere.
- [ ] No JS file changed; no other CSS rule changed.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces
  as a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` (n/a, no JS touched), `git diff --check`
  — all clean, real output pasted.

## Implementer Evidence (PM, self-implemented)

### Implementation summary

- `frontend/static/css/style.css`: extended `.btn[disabled]` to also match
  `.btn[aria-disabled="true"]` — 1 line changed, same shared values
  (`opacity: .58; cursor: not-allowed; pointer-events: none;`).
- `frontend/pages/music_library.html`: removed the fully-redundant local
  `.btn:disabled { opacity: 0.55; ... }` rule.
- `frontend/pages/step7_youtube.html`: removed the fully-redundant local
  `.btn[aria-disabled="true"] { opacity: 0.55; ... }` rule.
- `frontend/pages/step6_thumbnail.html`: reduced the local disabled-button rule to
  just `button[disabled]` (kept — genuinely needed for the page's bare
  `.template-option`/`.variant-card` buttons, which have no `.btn` class), corrected
  to `opacity: .58`; removed the fully-redundant local `.btn-sm` padding override.
- `tests/test_quick_wins_browser.py`: added 2 new tests —
  `test_disabled_and_aria_disabled_buttons_share_the_same_opacity` (parametrized over
  `/music`, `/step6`, `/step7`; injects a real disabled `<button class="btn">` probe
  and a real `<a class="btn" aria-disabled="true">` probe, asserts identical computed
  opacity — no hardcoded literal value, matching the Task 6.1 `accent-color` test's
  pattern) and `test_thumbnail_btn_sm_padding_matches_the_shared_rule` (compares a
  `.btn.btn-sm` probe's computed padding on `/step6` against `/step7`, an unrelated
  page that never had a local override).
- `.viepilot/requests/ENH-004.md`: updated with the corrected finding — no code
  changed; marked `wontfix` with full reasoning (see task card's "Current state"
  section above).
- `.viepilot/requests/ENH-005.md`: updated with PM Acceptance evidence, marked done
  for the concrete drift fixed here; noted the broader 992-line fragmentation
  observation was not fully audited (out of proportion to this task).

### Revert-and-confirm-failure check

Before trusting the new opacity test, reverted just `style.css` and
`music_library.html` via `git stash` and re-ran the `/music` parametrization to
confirm it actually fails without the fix (not a vacuously-true test):

```text
> venv\Scripts\python -m pytest "tests/test_quick_wins_browser.py::test_disabled_and_aria_disabled_buttons_share_the_same_opacity[/music]" -v
FAILED — AssertionError: assert '0.55' == '1'
```

Then `git stash pop` restored the fix; re-ran and confirmed it passes.

### Targeted and regression browser tests

Command:

```text
venv\Scripts\python -m pytest tests/test_quick_wins_browser.py tests/test_tts_shell_browser.py tests/test_thumbnail_shell_browser.py tests/test_youtube_shell_browser.py tests/test_music_library_browser.py -q
```

Output:

```text
...............................                                          [100%]
31 passed in 44.48s
```

### Ruff

Command:

```text
venv\Scripts\python -m ruff check app/ tests/
```

Output:

```text
All checks passed!
```

### Diff whitespace check

Command:

```text
git diff --check
```

Output: exit code 0, only Windows line-ending notices (no real whitespace errors).

### Full suite

Command:

```text
venv\Scripts\python -m pytest tests/ -q
```

Output:

```text
FAILED tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s
1 failed, 601 passed, 2 warnings in 1300.06s (0:21:40)
```

The 1 failure is the project's long-documented Gemini-retry/backoff timing flake
class (`tests/test_script_service.py`, unrelated to any of this task's 5 touched
files) — confirmed passing in isolation:

```text
venv\Scripts\python -m pytest tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s -v
tests/test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s PASSED [100%]
1 passed in 0.74s
```

### Scope confirmation

Command:

```text
git status --short
```

Output:

```text
 M .viepilot/phases/08-css-consolidation/tasks/task-8.1.md
 M .viepilot/requests/ENH-004.md
 M .viepilot/requests/ENH-005.md
 M frontend/pages/music_library.html
 M frontend/pages/step6_thumbnail.html
 M frontend/pages/step7_youtube.html
 M frontend/static/css/style.css
 M tests/test_quick_wins_browser.py
```

- No JS file was changed. No CSS rule outside `style.css` and the 3 page files was
  touched.
- `.viepilot/requests/ENH-004.md` was updated with findings only — no production code
  changed for ENH-004.

## PM Re-review (2026-09-18) — ACCEPTED

Self-implemented this task per the user's explicit request to save time, but held it
to the exact same independent-verification standard as any Codex-delivered task
rather than skipping review because there was no separate Implementer to check.

**Diff re-read in full**: confirmed all 4 production files changed exactly as
planned — `style.css`'s single-selector-list extension, `music_library.html`'s and
`step7_youtube.html`'s full rule removals, `step6_thumbnail.html`'s rule reduction to
`button[disabled]` only (kept for its bare `.template-option`/`.variant-card`
buttons — confirmed via `step6_thumbnail.js:89,123,161` that these are real
`<button>` elements with no `.btn` class) plus its `.btn-sm` override removal. No
other selector in any of the 3 pages' `<style>` blocks was touched.

**Test meaningfulness independently confirmed, not just written and trusted**: ran the
revert-and-confirm-failure check personally (`git stash` on `style.css` +
`music_library.html`, re-ran the `/music` parametrization, got the expected
`AssertionError: assert '0.55' == '1'`, then `git stash pop` and re-confirmed the pass)
— this is not a vacuously-true test.

**Re-ran every verification command independently**: 31/31 targeted+regression across
all 3 affected pages plus TTS (a control page that never had a local override), ruff
clean, `git diff --check` exit 0.

**Full suite, run independently**: 601 passed, 1 failed
(`test_generate_script_backoff_sequence_is_1s_2s_4s`) in 1300.06s — the project's
known Gemini-retry timing flake class, confirmed passing instantly in isolation
(0.74s), unrelated to any of this task's 5 touched files.

**ENH-004 re-scoping independently sound**: re-read `app/api/projects.py` lines 20-36
directly — confirmed the connection-wide `_write_lock` genuinely already serializes
every route (reads included), meaning WAL mode would indeed provide zero real benefit
without also removing that lock, which is correctly identified as a much larger
change than this task's scope. No code was changed for ENH-004, and none should have
been — implementing WAL alone would have been a decorative non-fix.

**Zero real defects found.** Accepted as delivered.

**This closes Task 8.1 — and Phase 8 (CSS Consolidation) in full**, since it was the
phase's only task. BUG-013 (Phase 7), ENH-005 (this task) are now resolved. ENH-004
is correctly re-scoped to `wontfix` with full reasoning recorded, not silently
dropped.
