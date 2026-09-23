# Phase 17 Gate B-8 — Local-Only Trial after the Budget-Aware Global Stage (17.1, 17.2)

- **Task:** 17.3 (PM). Protocol = Gate B-7 verbatim (5 × B1 8-min, 4 samples, learning, media on
  the first passing run, owner configuration A2 / small_talk / 10 min ×2). Local qwen3.5:9b,
  fresh trial DB, Coder idle, thresholds unchanged.
- **Run date:** 2026-09-23 (≈ 10:0x – 11:1xZ). **Code HEAD:** `6d07e8b` (17.1 + 17.2 accepted),
  suite 963/963.
- **Evidence (gitignored):** `data/quality_reviews/phase15/gate-b8/`
  - `gate-b8-20260923T105330Z.json` (SHA-256
    `21d7f0f92ad48b15d226af1547a2410bfe8caf19a17a4282259b2a16a9e995f6`)
  - `gate-b8-owner-config.json`, both console logs, `trial-data/app.db`

## 1. Results against Gate B-7

| Job | B-7 | **B-8** |
|---|---|---|
| B1 8-min ×5 | 4/5 complete (1 mixed word + repetition death) | **5/5 complete** (972 / 1,029 / 1,035 / 1,006 / 1,003 words; the repetition repair fired in 2 runs and recovered both) |
| Sample B1 5-min | error (703 / 625) | **complete** (671) |
| Samples B1 10-min / A2 / C1 | 3/3 | **3/3** (A2: the global budget repair fired and recovered the job) |
| Learning | 4/4 | **5/5** |
| Media | PASS 491.1 s | **PASS 456.3 s** (range 432–528), all 5 checks true |
| Repetition deaths | 0 (1 mixed) | **0** |
| **Owner config (A2/small_talk/10 min)** | **2/2** | **1/2**: run 2 **error**, total 1,377 vs target 1,110 |

- **Runner decision: PASS** ("all declared thresholds met").
- **Plan §3 17.3 criterion (B1 8-min 5/5, no regression on structural, learning, media or
  repetition): PASS.**
- **But the owner configuration regressed from 2/2 to 1/2**, and the cause is a 17.1 defect (§2).

## 2. Defect found: the "under" direction uses a plain repair, and it overshoots

Owner run 2, read from the trial checkpoints (read-only):
- **Before the global stage**, the total was **963**, *under* the range 999–1,221.
- **Selection was correct:** section 6 (91 words vs nominal 158, the largest under-deviation).
  The new target was 1,110 − (963 − 91) = **238**.
- **The plain `_repair_section` returned 505 words** (2.1× target). The total became **1,377**.
  The budget slot was spent, so the job failed.

The direction-specific choice in 17.1 C4 ("under" keeps a plain repair) was the PM's
instruction, and the PM's own evidence argued against it: 36/103 repaired sections in B-6/B-7
ended more than 15% *over*. The full per-section path (generate, then an in-loop length repair
when outside ±15%) lands at a median 1.02×, and its length repair self-corrects an overshoot
like this one. **Fix:** use the full per-section path for **both** directions.

## 3. Watch items from 17.1 and 17.2

- **Sign-off (17.2):** 10 of 11 completed scripts have a sign-off by `has_outro_last3`.
  - B1 run 5 is a runner false negative (`has_outro` False, `has_outro_last3` True), exactly the
    case 17.2's diagnostic exists for.
  - **Owner run 1 still ends with no goodbye**: its last three lines are forward-looking
    statements. The sign-off instruction was ignored once, by the A2 small_talk configuration.
    Watch it; don't act yet.
- **Rerun continuity (17.1 watch item 1):** no "over" rerun fired at B-8, so it wasn't observed.
- **Repair counts (17.1 watch item 2):** not comparable with B-7, by design.
