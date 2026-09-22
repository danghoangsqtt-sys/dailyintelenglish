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
