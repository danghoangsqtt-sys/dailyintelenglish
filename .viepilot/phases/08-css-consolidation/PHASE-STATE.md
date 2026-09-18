# Phase 8 State — CSS Consolidation

## Metadata
- **Phase:** 8
- **Slug:** 08-css-consolidation
- **Status:** complete
- **Started:** 2026-09-18
- **Closed:** 2026-09-18
- **Milestone Progress:** 1 / 1 task done. Opened at the user's explicit request to
  continue processing the remaining logged findings (ENH-004, ENH-005) and to save
  time by having PM self-implement rather than delegate to Codex for this task.
  Re-investigation before writing the task card changed ENH-004's scope
  significantly: the single shared DB connection is a deliberate, already-correct
  design (an existing code comment in `app/api/projects.py` documents exactly why —
  a connection-wide `asyncio.Lock` already serializes every route to prevent dirty/
  phantom reads on the single shared connection), and no small/low-risk fix exists —
  WAL mode alone would be purely cosmetic given that existing lock, and a real fix
  means a full connection-pool redesign, deferred per the project's standing
  precedent (Progress cancellation, LivePortrait lip-sync). ENH-004 is marked
  `wontfix` with full reasoning recorded, not silently dropped. ENH-005 (CSS
  fragmentation) had a real, minimal, fully-traced fix: the shared stylesheet was
  missing a `.btn[aria-disabled="true"]` variant of its `.btn[disabled]` rule, so 3
  pages each independently invented their own inconsistent local fix — reconciled to
  one shared rule, with the resulting redundant page-local overrides removed.
- **Test Suite Status:** 601/602 pass (2026-09-18, after Task 8.1) — the 1 failure is
  the project's long-documented Gemini-retry/backoff timing flake class, confirmed
  passing instantly in isolation. See TRACKER.md.

---

## Tasks Status & Acceptance Evidence

### Task 8.1: Reconcile disabled-button CSS drift (ENH-005); ENH-004 re-scoped — ✅ DONE (2026-09-18)
- **Status:** done
- Self-implemented by PM per explicit user request, a one-time deviation from the
  AR-06 PM/Codex split for this task only — held to the same doc-first plan,
  independent re-verification (including a revert-and-confirm-failure check proving
  the new tests are meaningful), and git-persistence gates as any Codex-implemented
  task. The shared `.btn[disabled]` rule in `frontend/static/css/style.css` now also
  matches `.btn[aria-disabled="true"]`, closing the real gap that caused
  `music_library.html`, `step7_youtube.html`, and `step6_thumbnail.html` to each
  invent their own inconsistent local override (opacity 0.55 vs the shared 0.58,
  across 3 different selector strategies). The now-redundant local overrides were
  removed; `step6_thumbnail.html` kept only its genuinely non-redundant
  `button[disabled]` selector (needed for bare `.template-option`/`.variant-card`
  buttons with no `.btn` class), corrected to the shared value. `step6_thumbnail.html`'s
  drifted `.btn-sm` padding override was also removed. 2 new Playwright tests added
  to `tests/test_quick_wins_browser.py`, verified meaningful via a real
  revert-and-observe check (`0.55` vs `1` before the fix). ENH-004 was
  re-investigated rather than blindly "fixed": found the single shared DB connection
  is already protected by an existing, well-reasoned connection-wide lock
  (`app/api/projects.py`'s `_write_lock`), so WAL mode alone would be a no-op —
  correctly marked `wontfix` with full reasoning, no code changed. 601/602 full
  suite passes (1 known Gemini-retry flake, confirmed non-regressive). See
  `tasks/task-8.1.md` for the full record.

**This closes Phase 8 (CSS Consolidation) in full**, since Task 8.1 was its only
task.
