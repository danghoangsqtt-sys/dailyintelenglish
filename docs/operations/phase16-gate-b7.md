# Phase 16 Gate B-7 — Local-Only Trial after the Anti-Repetition Rules (16.4)

- **Task:** 16.5 (PM execution). Protocol = Gate B-6 verbatim: 5 × B1 8-min, 4 samples, learning
  on every completed B1 run, media on the first passing run, plus the owner's configuration
  (A2 / small_talk / 10 min / 2 speakers) ×2 with learning. Local only, fresh trial DB,
  Coder idle, thresholds unchanged (invariant 24).
- **Run date:** 2026-09-23 (03:4xZ – 04:3xZ UTC)
- **Code HEAD:** `f5ebf0e` (16.1–16.4 accepted). Full suite **956/956** before the run; `ruff` clean.
- **Evidence (gitignored):** `data/quality_reviews/phase15/gate-b7/`
  - `gate-b7-20260923T034318Z.json` (SHA-256
    `078908dd9564a2adcaae8e0503e9a0e00af8a1ccccf392dbcb492f80e757ce71`)
  - `gate-b7-owner-config.json`
  - `local-matrix-console.log`, `owner-config-console.log`
  - `trial-data/app.db`

  Deviation: the runner's `--gate` flag hard-codes `phase15/`, so the evidence sits under
  `phase15/gate-b7/`, not the plan's `phase16/gate-b7/`. The content is unaffected. The
  owner-config driver was a PM scratch script. It reused the runner's own `run_script_trial` /
  `run_learning_trial` with `GENRE = "small_talk"`.

## 1. Side by side with Gate B-6 (same protocol, same model, same thresholds)

| Job | B-6 result | B-7 result |
|---|---|---|
| B1 8-min run 1 | complete, 1,056 w, rep 0.00% | **error**: word count 1,124 (> +10%) **and** rep 1.07% (mixed) |
| B1 8-min run 2 | **error**: rep 1.00% | complete, 1,064 w, rep 0.00% |
| B1 8-min run 3 | complete, 1,079 w, rep 0.37% | complete, 1,000 w, rep 0.00% |
| B1 8-min run 4 | complete, 1,053 w, rep 0.00% | complete, 1,015 w, rep 0.00%, *outro heuristic miss* (see §3) |
| B1 8-min run 5 | **error**: rep 1.42% | complete, 1,018 w, rep 0.00% |
| sample B1 5-min | complete, 636 w | **error**: word count 703 vs 625 (> +10%) |
| sample B1 10-min | complete, 1,348 w | complete, 1,261 w, rep 0.00% |
| sample A2 8-min | complete, 833 w, rep 0.12% | complete, 901 w, rep 0.00% |
| sample C1 8-min | complete, 1,292 w | complete, 1,174 w, rep 0.00% |
| owner A2/small_talk ×2 | 2/2, 1,100 / 1,073 w | 2/2, 1,184 / 1,051 w, rep 0.00%; run 1: *no explicit sign-off* (§3) |
| Learning | 3/3 + owner 2/2 | **4/4 + owner 2/2** |
| Media | PASS 487.3 s | **PASS 491.1 s** (range 432–528), all 5 media checks true |
| Structural failures | 0 | **0** |

## 2. Verdicts

- **Runner decision: FAIL.** "B1 8-minute script gate: 3/5 passed content checks (4/5
  completed), needed 4/5."
- **Plan §4 16.5 criterion (script 5/5 complete): FAIL.** 4/5 completed.
- **No regression** on any gate B-6 passed. Structural is 0, learning and media PASS, and
  media duration is still inside the range.

## 3. What the evidence says

1. **Repetition, 16.4's target, is effectively gone as a failure class.** All **9**
   completed scripts at B-7 have a repeated-8-gram ratio of **0.00%**. At B-6, two jobs died
   on repetition *alone*, and two completed scripts carried a non-zero ratio. The one B-7 job
   that tripped repetition (1.07%) did so together with a 12% word-count overshoot.
2. **The remaining failure class is the global word-count overshoot.** It hit 2 jobs: B1 run 1
   (1,124 / 1,000) and the B1 5-min sample (703 / 625). The pipeline has per-section length
   repairs, but **no repair for a global total overshoot**. A mixed failure (word count plus
   repetition) is also excluded from Task 14.13's repetition repair by design.
3. **Planned Task 16.6 would not have saved either failure.** 16.6 is a second
   repetition-*only* repair. Run 1's failure is mixed, and the 5-min sample's failure is word
   count only. Its trigger condition ("< 5/5 on repetition") is technically met, but the
   mechanism doesn't match the evidence.
4. **Outro heuristic.** B1 run 4 is a false negative in the runner's last-line check. A real
   sign-off ("It was a genuine pleasure talking to you both … we will be back very soon next
   episode") sits two lines before the last line. Owner run 1 ends on a call to action with no
   goodbye. B-6 had zero outro misses. It is possible, not proven, that rule 5 ("never repeat
   the same summary or takeaway sentence") makes the model skip a closing recap. This is a
   **watch item** for the next gate.

## 4. Recommendation (for the owner)

Close Phase 16 with ENH-009 marked **resolved on evidence** (repetition 0.00% in 9/9 completed
scripts). Do **not** run 16.6 as specified. Log the global word-count overshoot as a new request
(ENH-010: a bounded global length repair for a total over +10%, including the mixed
word-count-plus-repetition case) and the outro-heuristic / rule-5 watch item for the next phase.
Until then, a failed job costs about 2–3 minutes and the in-app Retry recovers it, with no data
corruption.
