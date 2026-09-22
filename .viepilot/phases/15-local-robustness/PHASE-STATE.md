# Phase 15 State — Local Script Robustness (Structural Failures)

## Metadata

- **Phase:** 15
- **Slug:** `15-local-robustness`
- **Status:** in_progress
- **Started:** 2026-09-22
- **Closed:** —
- **Controlling plan:** `docs/implementation/phase-15-local-robustness.md`
- **Authorization:** the owner's first hands-on real run after Phase 14 closed died at
  section 3 (`section_validation_failed: unknown speaker_id(s):
  ['ff5f20e0-417b-8d9f-752e844d46f0']` against the real id
  `ff5f20e0-4082-417b-8d9f-752e844d46f0`, Alex — the model dropped one UUID group).
  PM verified the failure directly against `data/app.db` (read-only): sections 1–2 had
  completed with repairs, 3 repairs total, died on the structural check. The owner
  opened Phase 15 (`/vp-auto`, 2026-09-22) under delegated decision authority. Execution
  runs as the same two parallel sessions (PM: Claude Opus 5; Coder: Claude Sonnet 5)
  under the Phase 14 §10 file partition, unchanged.
- **Ownership of this folder:** Coder from creation (PM authored the controlling plan in
  `docs/implementation/`, not this folder). The PM reads and requests edits.

## Preflight

- Branch `main`; upstream `origin/main`; Phase 14 closed 2026-09-22 (`8ecade0`, tags
  `die-vp-p13-complete`/`die-vp-p14-complete`).
- Full suite baseline: **902/902 pass** (Task 14.13's closing number), `ruff` clean.
- Real failure evidence: the owner's own project (A2, small_talk, 10 minutes, 2
  speakers) died at section 3 on `section_validation_failed: unknown speaker_id(s)`.
  The same failure *class* (not the same exact bug) killed the B1 5-minute sample at
  Gate B-4 (`unknown speaker_id`, truncated UUID) and the B1 10-minute sample at
  Gate B-3 (consecutive-lines rule) — three real, independent hits of the same two
  structural checks across three different evidence sources.

## Task status

| Task | Description | Owner | Status | Blocking gate |
|---|---|---|---|---|
| 15.1 | Speaker aliases in the section contract (deterministic id resolution) | Coder | **done** (915 passed, 0 failed) | see task-15.1.md verification |
| 15.2 | Deterministic consecutive-lines fix (merge, never re-attribute) | Coder | **done** (926 passed, 0 failed) | see task-15.2.md verification |
| 15.3 | Trial runner per-gate evidence path + `set_job_metric` layering | Coder | pending | Depends on 15.2 done |
| 15.4 | Gate B-6, local only (owner's failing config as a 5th sample) | PM | pending | Depends on 15.1–15.3 done; Coder idle during the run |
| 15.5 | Multi-script pace calibration (optional, owner's word only) | PM → Coder | not started | Deferred until 15.1–15.4 land; only if the owner asks |

**Execution order:** 15.1 → 15.2 → 15.3 (Coder, doc-first cards reviewed by the PM
before code, sequential) → 15.4 (PM; Coder idle) → close-out. 15.5 only on the owner's
explicit word.

## Decisions

- Invariant 20: no invented speaker, ever — server-side mapping may *resolve* an alias
  or a near-miss to a real speaker; it may never *choose* one the model did not
  indicate.
- Invariant 21: no content invented by the server — a structural fix reorders or
  merges lines; it never edits a line's words.
- Invariant 22: `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5`, both word tolerances,
  and `SCRIPT_MAX_REPEATED_8GRAM_RATIO` stay pinned, unchanged for this phase.
- `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 0.85` (difflib safety net for a near-UUID) and
  `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1` (one merge attempt per section) are new
  constants Task 15.1/15.2 introduce; rollback sets the former to `1.0` and the latter
  to `0` to restore Phase 14 behavior without a code revert.
- Legacy single-line `regenerate_line` (`script_service`) is explicitly out of scope
  for Task 15.1 — it still echoes ids; noted, not touched.
- Pace calibration is **not** re-measured in this phase (Task 15.5 is optional and
  deferred); Gate B-6 reports the media gate as declared, same as Gate B-5.

## Evidence log

- 2026-09-22: Phase 15 opened (`433b215`, PM). Coder read the controlling plan and is
  mirroring §3's four Coder tasks (15.1–15.3) plus the two PM-owned description-only
  cards (15.4, 15.5) into this folder, doc-first, before any implementation file is
  touched — awaiting the PM's review of the cards before starting 15.1.
- 2026-09-22: PM accepted the cards, added two review notes (display-name
  resolution only when unique; the safety net gated to UUID-shaped values only,
  requiring an unambiguous single match), and authorized starting 15.1 -- the
  owner is waiting on this fix to retry their failed run. Coder implemented it,
  doc-first: a new `SectionLineWire` model (`speaker: str`, the alias) is what
  the AI actually parses/schemas against; `SectionLineOut` (`speaker_id: str`,
  UUID) is completely unchanged and stays what every downstream consumer
  (validators, checkpoints, `script_service.save_script`) uses -- which is also
  why resume compatibility needed no special-casing: checkpoints have always
  stored the resolved shape, before and after this task. `resolve_speaker`
  tries, in order: exact alias, alias case/whitespace-insensitive, unique
  display name, exact UUID, then a difflib safety net (UUID-shaped values only,
  `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 0.85`, exactly one match required) --
  anything else passes through unresolved into the existing unknown-speaker
  check, unchanged. Verified directly against the real trigger case
  (`ff5f20e0-417b-8d9f-752e844d46f0` -> the real
  `ff5f20e0-4082-417b-8d9f-752e844d46f0`, Alex, ratio 0.925) before wiring it
  into the pipeline. Wiring the new wire adapter into `_generate_section`/
  `_repair_section` broke all 19 of this file's e2e tests at once (every
  `FakeProvider` fixture used the old `"speaker_id"` wire shape) -- fixed at
  the two JSON-building test helpers (rename the key to `"speaker"`, keep
  passing each test's real UUID as the value, which resolves via the
  `uuid_exact` rule unchanged) plus one file-wide literal replace, not by
  editing any test body. `section.txt`/`repair.txt` now present speakers as
  `S1`/`S2` aliases. `regenerate_line` (`script_service.py`) confirmed
  untouched, exactly as the card's explicit out-of-scope note requires. 13 new
  tests (10 pure, 3 e2e, incl. the literal real-world example and an
  equidistant-tie-is-unknown case). Revert-and-confirm-failure done twice: the
  constants pin, and separately the safety net's own behavior at the card's
  documented rollback value (`1.0`, exact-match-only). Full suite: **915
  passed, 0 failed**. Task 15.1 status: **done**.
- 2026-09-22: PM accepted Task 15.1 (independently called `resolve_speaker`
  directly on the real trigger case, confirmed `uuid_near_miss`), added a
  review note for 15.2 (merge's `language_notes` handling; confirmed word
  count is provably invariant across a merge), and authorized starting 15.2.
  Coder implemented it, doc-first: `merge_consecutive_lines` splits each
  over-limit same-speaker run into exactly `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`
  contiguous groups via the same `divmod` distribution `plan_sections` already
  uses, joining each group's text with a space (word order and content
  provably unchanged); `_merge_group` unions `collocations`/`idioms`
  (deduplicated, first-seen order) and keeps the first line's `grammar_point`,
  per the PM's note. The "whole section is one speaker" unfixable case (the
  plan's own example) is detected directly (`< 2` distinct speaker ids in the
  section) rather than left for the merge algorithm to fail on its own, since
  chunking a single run can always numerically satisfy the raw limit --
  merging a true monologue into fewer giant paragraphs would still not be a
  dialogue. Bounded by new `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1`; fires
  only when the post-repair structural error is *exactly* the consecutive-lines
  one (never mixed with unknown-speaker). Checkpoint metrics gain
  `structural_fix`/`lines_before_fix`/`lines_after_fix`. 11 new tests (9 pure,
  2 e2e); found and fixed two fixture mistakes while writing the e2e
  success case (an imbalanced 98/2 word split tripping the *separate*
  speaker-balance check; looking up the wrong checkpoint by list index instead
  of `section_index`) -- neither was a bug in the merge fix itself. Recorded
  one small, reasoned deviation from the card's own "constants pin extended"
  wording: checked the precedent first and found neither of the two prior
  repair-*budget* constants (Task 14.8/14.13) are in that threshold-governance
  pin test either -- matched that established pattern instead, and did a more
  meaningful revert-and-confirm-failure on the constant's actual gating
  behavior (0 disables the pass, the exact pre-Task-15.2 hard-fail returns)
  rather than a static pin assertion. Full suite: **926 passed, 0 failed**.
  Task 15.2 status: **done**.
