# Phase 15 Gate B-6 — Local-Only Trial after the Structural Fixes (15.1–15.3)

- **Task:** 15.4 (PM execution). Protocol = Gate B-5 (Phase 13 §8 13.9 verbatim at the D13
  targets, level-default speeds) **plus the owner's own failing configuration** (A2 /
  small_talk / 10 min / 2 speakers) as an extra sample, run twice. Thresholds unchanged.
- **Run date:** 2026-09-22 (09:1x–10:2xZ UTC)
- **Code HEAD:** `d2c0d20` (15.3). Full suite **932/932** before the run; `ruff` clean.
- **Evidence (gitignored), now on the per-gate path from 15.3:**
  `data/quality_reviews/phase15/gate-b6/gate-b6-20260922T095127Z.json` (SHA-256
  `6a29a4aa13683fd8454bbba4864717e23981ede7ebb0e03915431127242b39a2`),
  `gate-b6-owner-config.json`, both console logs, `trial-data/app.db` (fresh DB for this gate).

## 1. Primary set — five B1 eight-minute jobs at 1,000 words

| Run | Status | Seconds | Words | Repairs (total / length / repetition) | Result |
|---|---|---:|---:|---|---|
| 1 | **complete** | 150.6 | **1,056** | 7 / 2 / 0 | all 7 content checks pass |
| 2 | error | 150.5 | — | 7 / 2 / **1** | `repeated 8-gram ratio 1.00% ≥ 1%` (after the repetition repair) |
| 3 | **complete** | 265.0 | **1,079** | 4 / 1 / 0 | all pass |
| 4 | **complete** | 120.5 | **1,053** | 5 / 0 / 0 | all pass |
| 5 | error | 147.6 | — | 7 / 1 / **1** | `repeated 8-gram ratio 1.42% ≥ 1%` (after the repetition repair) |

**3/5 complete, 3/3 of those pass.** Infra 0, `handler_exception` 0, max attempts 2.
**Zero structural failures** — no unknown speaker, no consecutive-lines death — in the
whole trial (9 matrix jobs + 2 owner-config jobs); Phase 15's target failure class did not
occur once, and `structural_fix` never needed to fire. Both deaths are repetition: the one
bounded repetition repair fired in each and was not enough (1.00% is exactly the threshold).
Same code produced 5/5 in Gate B-5 and 3/5 here — repetition is now the dominant *and
variable* residual, not a regression.

Aggregates: within ±15% of nominal 36%; repair success 48%; σ 30.1%; total repairs 30
(more repairs than B-5 — the model ran long more often this time; all five totals that
completed sit in 1,053–1,079).

## 2. Samples — 4/4 complete

| Run | Words / target | Repairs | Runner checks |
|---|---|---|---|
| B1 5-min | 636 / 625 | 4 | all pass |
| B1 10-min | 1,348 / 1,250 | 9 | all pass |
| A2 8-min | 833 / 888 | 7 (1 repetition) | all pass |
| C1 8-min | 1,292 / 1,160 | 6 | `word_count_in_range` false (+11.4% by the runner's count; the pipeline's own ±10% gate passed on its count — the two counters differ by a few tokens on hyphens/contractions, disclosed, not investigated further since samples are informational), `intro_present` false (heuristic) |

## 3. The owner's configuration — A2 / small_talk / 10 minutes / 2 speakers, run twice

| Run | Status | Seconds | Words / target | Repairs | Learning |
|---|---|---:|---|---|---|
| 1 | **complete** | 187 | **1,100** / 1,110 | 8 | complete |
| 2 | **complete** | 166 | **1,073** / 1,110 | 8 | complete |

The configuration that died on a copied-UUID slip in the owner's hands now completes,
twice, with learning — on the same model, with speaker aliases in the contract.

## 4. Learning — 3/3 on the matrix, 2/2 on the owner's configuration

## 5. Media (winning project = run 1, 1,056 words, 44 lines, speed 0.85) — **PASS, first time**

| Step | Result |
|---|---|
| Real Edge TTS | 44/44 |
| Mix | 200; **487.33 s**, MP3 9,748,364 bytes, `2703b0d2…` |
| Render | 200; **487.33 s**; MP4 9,617,547 bytes, h264/aac, `367b99f3…` |
| Checks | **duration 487.3 s ∈ [432, 528] ✔**, **A/V diff 0.00 s ✔**, codecs ✔ |

D13 (measured pace calibration) is confirmed end to end: a script near the 1,000-word
target at the B1 default speed plays for ≈ 8 minutes (487 s = 8:07).

## 6. Decision (Phase 13 Gate B rule, unchanged)

| Gate | Result |
|---|---|
| Script 5/5 complete, ≥ 4/5 pass | **FAIL — 3/5** (repetition) |
| Learning | PASS 3/3 (+ 2/2 owner) |
| Media 432–528 s, A/V ≤ 1.0 s, codecs | **PASS** (first time) |
| Timing / infra | PASS |
| Structural failures (Phase 15's objective) | **0 in 11 jobs** |

**Overall Gate B-6: FAIL on the script gate (repetition), PASS on every other gate.**
Phase 15 achieved what it set out to do — the structural failure class is gone from the
evidence — and closes here. No threshold was changed.

## 7. What is left (for the owner)

Repetition is the single remaining failure class and it is variable run-to-run (B-5
5/5, B-6 3/5 on identical code; both B-6 deaths were within 0.42 points of the 1%
threshold after one repair). Options, none started: allow a second bounded repetition
repair targeting the next-worst section; strengthen the section prompt's "avoid" list
(currently the top 8 repeated 8-grams) with the specific framing phrases the model reuses
(they are visible in the checkpoints); or accept a 3–5 /5 completion rate with the
in-app Retry button, since a failed job costs ~2.5 minutes and never corrupts anything.
The multi-script pace calibration (15.5) is no longer needed for the media gate to pass
at B1; it remains optional for the other levels.

## 8. Evidence

| File | SHA-256 / note |
|---|---|
| `phase15/gate-b6/gate-b6-20260922T095127Z.json` | `6a29a4aa13683fd8454bbba4864717e23981ede7ebb0e03915431127242b39a2` |
| `phase15/gate-b6/gate-b6-owner-config.json` | owner-configuration runs (2 script + 2 learning) |
| `…/c542ee14-…-audio.mp3` / `-video.mp4` | `2703b0d24f6634f4…` / `367b99f386044604…` |
| `phase15/gate-b6/local-matrix-console.log`, `owner-config-console.log` | no key, no prompt text |
