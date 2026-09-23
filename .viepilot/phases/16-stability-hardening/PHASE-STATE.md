# Phase 16 State — Stability Hardening

## Metadata

- **Phase:** 16
- **Slug:** `16-stability-hardening`
- **Status:** complete
- **Closed:** 2026-09-23 (owner decision D20)
- **Opened:** 2026-09-23
- **Controlling plan:** `docs/implementation/phase-16-stability-hardening.md`
- **Authorization:** the owner ran `/vp-audit` (2026-09-23) and then `/vp-evolve` for
  BUG-022, ENH-008, ENH-009 and BUG-023, with decisions D18 (ENH-009: prompt first, then
  a second repair only if Gate B-7 < 5/5) and D19 (BUG-023: delete the leaked test
  projects, with a backup, after a dry-run).
  Execution uses two parallel sessions: PM (Claude Opus, session "Phân tích mã nguồn dự
  án") and Coder (Claude Sonnet), under plan §6.
- **Ownership of this folder:** PM until the handover commit, Coder after it.

## Preflight

- Branch `main`, upstream `origin/main`. Phase 15 closed (`772c4eb`, tag
  `die-vp-p15-complete`).
- Baseline (2026-09-23 audit): **932/932 pass** (771 unit/API + 161 browser), `ruff` clean,
  `check_dependencies.py` all green, `data/app.db` `integrity_check` ok, 0 stuck jobs.
- Real DB: 426 projects, of which 419 are leaked fixtures (4 names), the newest from
  2026-09-22T09:51:09Z.

## Task status

| Task | Description | Owner | Status | Blocking gate |
|---|---|---|---|---|
| 16.1 | Worker loop guard + `worker_alive` (BUG-022) | Coder | done | — |
| 16.2 | ffmpeg timeouts (ENH-008) | Coder | done | — |
| 16.3 | Test-data leak root cause + guard + cleanup script + CHANGELOG Phase 15 (BUG-023) | Coder → PM | done | — |
| 16.4 | Repetition: evidence-driven avoid list (ENH-009 A) | Coder | done | — |
| 16.5 | Gate B-7, local only | PM | **done**: FAIL on word count (2 jobs), repetition 0.00% in 9/9 | see `docs/operations/phase16-gate-b7.md` |
| 16.6 | Second bounded repetition repair (ENH-009 B) | Coder | not run (D20) | would not address B-7's failures |
| 16.7 | Gate B-8 | PM | not run (D20) | — |

**Execution order:** 16.1 → 16.2 → 16.3 → 16.4 → 16.5 → (16.6 → 16.7) → close-out.

## Decisions

- D18 (owner, 2026-09-23): ENH-009 → prompt first (16.4), measure (16.5), second
  repair (16.6) only if needed. The threshold stays at 1%.
- D19 (owner, 2026-09-23): BUG-023 → delete only the 4 known fixture names, with a
  backup, after a dry-run shown to the owner. The PM runs `--apply`.

- D20 (owner, 2026-09-23): close Phase 16 after Gate B-7; 16.6/16.7 not run; ENH-010 logged.

## Evidence log

(Coder and PM append per task: commit sha, suite count, review verdict.)
