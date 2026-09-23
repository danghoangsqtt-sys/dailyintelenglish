# Phase 16 Summary — Stability Hardening

- **Status:** complete
- **Opened / closed:** 2026-09-23 / 2026-09-23 (owner decision D20)
- **Controlling plan:** `docs/implementation/phase-16-stability-hardening.md` (Amendments A–D)
- **Trigger:** `/vp-audit` 2026-09-23 found 932/932 green, but four stability gaps.

## Tasks

| Task | Result | Commits |
|---|---|---|
| 16.1 Worker loop guard + `worker_alive` (BUG-022) | Loop survives any per-iteration error; liveness shown on `/api/ai/health` | `f925ea5`, `56bb74b` |
| 16.2 ffmpeg timeouts (ENH-008) | Timeout = max(300 s, 4 × audio). Temp render + atomic replace, so a failed or timed-out re-render never destroys the previous video. Actionable error when the file is in use | `17cb199`, `95d8b29`, `4baa840` |
| 16.3 Test-DB leak (BUG-023) | Root cause: 24 copy-pasted live-server fixtures, 21 not isolating `DATA_DIR`. Now one shared helper, plus a guard against the real DB and stale reuse. PM cleanup: 447 leaked projects deleted, 7 kept, backups taken | `48e52b6`, `22100d0` |
| 16.4 Anti-repetition rules (ENH-009 A) | 3 abstract, evidence-traced rules in `section.txt` + 1 in `repair.txt`, no code change | `e5be873`, `d6ecbb7` |
| 16.5 Gate B-7 | Repetition 0.00% in 9/9 completed scripts; FAIL on 2 global word-count overshoots | `ce6eff0` |
| 16.6 / 16.7 | Not run (D20) | — |

Suite: 932 → **956**, `ruff` clean. Every task was PM-reviewed with an independent revert check.

## Residuals

- **ENH-010**: no repair for a global word-count overshoot (> +10%), including the mixed
  word-count + repetition case. This is now the dominant script failure class.
- **Watch item**: the outro heuristic missed 2 scripts at B-7. One is a runner false negative;
  one has a genuinely missing sign-off. A possible interaction with 16.4's rule 5 should be
  re-checked at the next gate.
- The runner's `--gate` hard-codes `phase15/`, so Gate B-7's evidence lives under
  `data/quality_reviews/phase15/gate-b7/`.
- N5: the cleanup script backs up with `shutil.copy2`. This was mitigated operationally by the
  PM's SQLite-API backup.
