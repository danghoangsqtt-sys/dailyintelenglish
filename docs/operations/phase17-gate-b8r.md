# Phase 17 Re-Gate (17.5) — after the "under" fix (17.4)

- **Protocol (plan Amendment C):**
  - 5 × B1 8-min (runner `--skip-samples`, with learning and media);
  - 4 × the owner configuration (A2 / small_talk / 10 min / 2 speakers), with learning.

  Local qwen3.5:9b, fresh trial DB, Coder idle, thresholds unchanged.
- **Run date:** 2026-09-23 (≈ 14:1x – 15:1xZ). **Code HEAD:** 17.4 accepted (`5008792`), suite 964/964.
- **Evidence (gitignored):** `data/quality_reviews/phase15/gate-b8r/`
  - `gate-b8r-20260923T144938Z.json` (SHA-256
    `a67b64515644961e763116b83013fc90986c9cc256b5a545938a8c9a00998bb2`)
  - `gate-b8r-owner-config.json`, both console logs, `trial-data/app.db`

## Results

| Job | Result | Global-stage repairs that fired (and recovered the job) |
|---|---|---|
| B1 8-min run 1 | complete, 1,024 w, rep 0.00% | — |
| B1 8-min run 2 | complete, 995 w | budget **over** + repetition |
| B1 8-min run 3 | complete, 1,020 w | budget **over** + repetition |
| B1 8-min run 4 | complete, 1,043 w, rep 0.10% | — |
| B1 8-min run 5 | complete, 1,013 w | repetition |
| Owner config 1 | complete, 1,090 w, learning ✓ | budget **under** (the exact B-8 defect path, now recovered) |
| Owner config 2 | complete, 1,159 w, learning ✓ | — |
| Owner config 3 | complete, 1,109 w, learning ✓ | repetition |
| Owner config 4 | complete, 1,116 w, learning ✓ | — |
| Learning | 5/5 B1 + 4/4 owner | |
| Media | PASS, 478.2 s (range 432–528) | |

The runner decision reads `DIAGNOSTIC_ONLY`, as expected with `--skip-samples`. Its own reason line
says "all declared thresholds met".

**Amendment C criterion:**
- B1 5/5 ✅
- Owner config ≥ 3/4 → **4/4** ✅
- 0 budget-repair overshoot deaths ✅
- No regression against B-8 on learning, media or repetition ✅

**→ 17.5 PASS.**

Every global-stage repair that fired recovered its job: 2 over, 1 under, 4 repetition.

## Residual watch item

**Sign-off:** owner config run 2 again ends with no goodbye (`has_outro` and `has_outro_last3` both
false). That is the second occurrence, both in the A2 small_talk configuration (B-8 owner run 1,
then here); every other script this gate has one. This is not gated. It is carried into Phase 18,
where the cloud primary follows instructions much more closely. Re-check there before any prompt
change.
