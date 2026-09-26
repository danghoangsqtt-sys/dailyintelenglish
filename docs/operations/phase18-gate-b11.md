# Phase 18 Gate B-11 — Gemini-first chain after 18.9

- **Task:** 18.10 (PM, Coder idle). Protocol = B-10: 5 × B1 8-min, 4 samples, learning, media,
  owner configuration ×2, run with `--matrix cloud_first`.
  - **Chain (D30):** `gemini-3.1-flash-lite` → `gemini-flash-lite-latest` → OpenRouter (Nemotron 3
    Super → Gemma 4 → Dots3) → local qwen3.5:9b.
- **Pre-gate live contract check** (the app's exact request body, 1 request per vendor):
  `gemini-3.1-flash-lite: OK`, `gemini-flash-lite-latest: OK`, `openrouter: OK`.
- **Run date:** 2026-09-26 (≈ 04:1x – 04:3xZ). **Code HEAD:** 18.9 accepted (`f3a0de3`), suite
  1173/1173.
- **Evidence (gitignored):** `data/quality_reviews/phase15/gate-b11/`
  - `gate-b11-20260926T042435Z.json` (SHA-256
    `438bcb6c991aa50ef5732d36637646b96e45039847e81b32c879e3536cbf4387`)
  - owner-config JSON, both console logs, `trial-data/app.db`
  - Secret-pattern scan: **0**.

## 1. Results

| Job | Status | Words | Served by | Repairs | Wall time |
|---|---|---|---|---|---|
| B1 8-min 1 | complete | 1,006 | Gemini 3.1 FL ×11 | 5 | 39 s |
| B1 8-min 2 | complete | 1,001 | Gemini 3.1 FL ×11 | 5 | 36 s |
| B1 8-min 3 | complete | 1,016 | Gemini 3.1 FL ×11 | 5 | 45 s |
| B1 8-min 4 | complete | 1,007 | Gemini 3.1 FL ×11 | 5 | 48 s |
| B1 8-min 5 | complete | 1,001 | Gemini 3.1 FL ×11 | 5 | 54 s |
| Sample B1 5-min | complete | 593 | Gemini 3.1 FL ×7 | 3 | 30 s |
| Sample B1 10-min | complete | 1,255 | Gemini 3.1 FL ×15 | 7 | 60 s |
| Sample A2 8-min | complete | 852 | Gemini 3.1 FL ×8, FL-latest ×2, local ×1 | 5 | 63 s |
| Sample C1 8-min | complete | 1,147 | Gemini FL-latest ×11 | 5 | 36 s |
| Owner config 1 | complete, learning ✓ | 1,130 | Gemini 3.1 FL ×15 | 7 | 45 s |
| Owner config 2 | complete, learning ✓ | 1,096 | Gemini 3.1 FL ×15 | 7 | 90 s |

- **All 11 jobs completed.** Repetition 0.00% everywhere. Learning 5/5 + 2/2. Media PASS
  504.1 s.
- **Answered calls:** Gemini 3.1 FL 115, Gemini FL-latest 13, local 1 (one
  `SchemaValidationError` local retry, from 18.6 item 4). OpenRouter wasn't needed.
- **B1 median wall time: 45 s**, against ~150 s on local qwen (B-8 / 17.5) and 409 s at B-10.
  That is **~3× faster than local.**

## 2. Runner decision FAIL — the outro heuristic, verified against the text

The runner reports "B1 8-minute script gate: 3/5 passed content checks (5/5 completed)". Runs 1
and 2 fail only `has_outro`, which looks for a fixed marker list in the **last** line. The PM read
the actual endings:
- **Run 1:** "We truly appreciate you tuning in to explore these health concepts with us. … We
  look forward to seeing you in our next session at Daily Intel English Studio."
- **Run 2:** "Thank you for being part of our community and for joining us on this enlightening
  episode … we eagerly anticipate welcoming you back here for another session next week."

Both are real sign-offs, phrased in a way the marker list doesn't cover. These are **measurement
false negatives, not content defects.** (Run 2's `has_outro_last3` is also true.)

## 3. Verdict

| Criterion (Amendment D) | Result |
|---|---|
| B1 5/5 complete | ✅ 5/5 |
| Samples ≥ B-8 (4/4) | ✅ 4/4 |
| B1 median wall time ≤ 1.5× local | ✅ **0.3×** (45 s vs ~150 s) |
| Runner content checks | ❌ 3/5, on outro-heuristic false negatives (§2), verified as real sign-offs |

**The PM recommends PASS**, with the heuristic disagreement stated openly. The owner makes the
final call (flip the `AI_MODE` default to `cloud_first`, Amendment C).

## 4. Follow-ups (not blocking)

1. **The outro heuristic:** widen the runner's sign-off markers (e.g. "tuning in", "joining us",
   "next session", "welcoming you back"), or switch the gate decision to `has_outro_last3`. This
   is a runner-only change, and it must be decided *before* the next gate so the goalposts don't
   move mid-gate.
2. **Gemini first-pass length:** in the full section prompt, Gemini's first pass lands at a median
   **0.61×** the section target, so every section needs one repair (5 repairs per B1 job). A
   bare-task probe got 1.00×. Tuning the section prompt for the cloud primary could roughly halve
   the calls per job, making it faster still and cheaper in quota.
3. **Quota headroom:** a B1 job uses ~11 Gemini calls. Gemini's free per-model daily limits (per
   project, reset at midnight PT) should be read from AI Studio before heavy daily use.
   OpenRouter and local remain as fallbacks.
