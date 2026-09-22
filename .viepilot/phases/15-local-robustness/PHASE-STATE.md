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
| 15.1 | Speaker aliases in the section contract (deterministic id resolution) | Coder | pending | P0 — real owner-run example is a literal test case |
| 15.2 | Deterministic consecutive-lines fix (merge, never re-attribute) | Coder | pending | Depends on 15.1 done |
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
