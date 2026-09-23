# Phase 16 State — Stability Hardening

## Metadata

- **Phase:** 16
- **Slug:** `16-stability-hardening`
- **Status:** planned (handover to Coder pending)
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
| 16.4 | Repetition: evidence-driven avoid list (ENH-009 A) | Coder | done (pending PM ACCEPTED) | PM diff review + revert check |
| 16.5 | Gate B-7, local only | PM | not started | Coder idle |
| 16.6 | Second bounded repetition repair (ENH-009 B) | Coder | conditional (only if B-7 script < 5/5) | — |
| 16.7 | Gate B-8 | PM | conditional (only if 16.6 ran) | — |

**Execution order:** 16.1 → 16.2 → 16.3 → 16.4 → 16.5 → (16.6 → 16.7) → close-out.

## Decisions

- D18 (owner, 2026-09-23): ENH-009 → prompt first (16.4), measure (16.5), second
  repair (16.6) only if needed. The threshold stays at 1%.
- D19 (owner, 2026-09-23): BUG-023 → delete only the 4 known fixture names, with a
  backup, after a dry-run shown to the owner. The PM runs `--apply`.

## Evidence log

(Coder and PM append per task: commit sha, suite count, review verdict.)
