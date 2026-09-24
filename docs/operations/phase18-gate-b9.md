# Phase 18 Gate B-9 — cloud_first (free Nemotron 3 Super) vs local

- **Task:** 18.5 (PM, Coder idle). Protocol = Gate B-8 (5 × B1 8-min, 4 samples, learning, media,
  owner configuration A2 / small_talk / 10 min ×2), run with `--matrix cloud_first`.
  - Primary: `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter, using the owner's key from
    `.env`.
  - Fallback: local qwen3.5:9b.
  - Thresholds unchanged; fresh trial DB.
- **Run date:** 2026-09-24 (≈ 05:4x – 07:3xZ). **Code HEAD:** `cb3fec7` (18.1–18.4 accepted),
  suite 1060/1060.
- **Pre-flight:** 6 probe calls, 5 OK and 1 `503 overloaded`. Seven of the day's free requests
  (the probes plus one earlier check) were used before the gate.
- **Evidence (gitignored):** `data/quality_reviews/phase15/gate-b9/`
  - `gate-b9-20260924T070428Z.json` (SHA-256
    `14eaa7dda5cfae40641aaa57b2fffc0042477a0cc02d05c0bc5f85d60eb1112c`)
  - `gate-b9-owner-config.json`, both console logs, `trial-data/app.db`
  - **Key-leak scan of all four evidence files: 0 matches for `sk-or`.**

## 1. Results

| Job | Status | Words | Model calls (cloud / local) | Repairs | Fallback calls | Wall time |
|---|---|---|---|---|---|---|
| B1 8-min 1 | complete | 983 | 6 (5 / 1) | 0 | 1 | 479 s |
| B1 8-min 2 | complete | 1,027 | 7 (6 / 1) | 1 | 1 | 551 s |
| B1 8-min 3 | complete | 1,033 | 7 (7 / 0) | 1 | 0 | 313 s |
| B1 8-min 4 | complete | 984 | 6 (5 / 1) | 0 | 1 | 280 s |
| B1 8-min 5 | complete | 1,023 | 9 (6 / 3) | 3 | 3 | 828 s |
| Sample B1 5-min | **error** | — | 4 (3 / 1) | 1 | 1 | 331 s |
| Sample B1 10-min | complete | 1,353 | 12 (6 / 6) | 4 | 4 | 566 s |
| Sample A2 8-min | complete | 876 | 12 (0 / 12) | 6 | 2 | 148 s |
| Sample C1 8-min | complete | 1,241 | 14 (0 / 14) | 7 | 2 | 187 s |
| Owner config 1 | complete, learning ✓ | 1,096 | 16 (0 / 16) | 8 | 5 | 205 s |
| Owner config 2 | complete, learning ✓ | 1,158 | 17 (0 / 17) | 9 | 3 | 262 s |

Other results: learning 5/5 + owner 2/2, media PASS 462.7 s, repetition deaths 0, structural 0.
The runner decision is **PASS** ("all declared thresholds met"). The matrix's call fallback rate
is 0.171.

**Fallback reasons across all 110 calls:**

| Reason | Calls |
|---|---|
| `ProviderRateLimitError` (429) | 15 |
| `ProviderTimeoutError` (the 150 s cloud budget) | 7 |
| `ProviderUnavailableError` (503) | 1 |

The **sample B1 5-min** job died with `Provider response is not valid JSON` (truncated at about
char 3,600). A cloud response came back syntactically broken, and the repair (also cloud) did not
recover it.

## 2. What the numbers mean

1. **Accuracy: better, as expected.** While the cloud actually served the job, B1 runs needed only
   6–9 calls and **0–3 repairs**, against 10–14 calls and 4–7 repairs on local qwen (B-8 / 17.5).
   Word counts landed on target and repetition was ~0.
2. **Speed: much worse on the free tier.** Cloud-served B1 jobs took **280–828 s (4.7–13.8 min)**
   against **~100–180 s** on local qwen. The causes:
   - free-tier latency;
   - **7 cloud timeouts, each burning up to the full 150 s budget** before the fallback ran.
3. **Free quota ran out mid-gate.** OpenRouter's free models allow **50 requests/day** for
   accounts with less than $10 of lifetime credit purchases, and 20/min. With the 7 pre-flight
   calls, the gate hit the cap during the B1 10-min sample. From then on every job ran on
   local qwen. **The fallback worked exactly as designed:** all four of those jobs completed.
   But each cloud attempt first cost a 429 round-trip, and 50 requests/day covers only about
   **5 scripts**.
4. **A new failure class:** malformed JSON from the cloud model (1 job). The pipeline treats it as
   a content error and repairs it via the same (cloud) route. There is no local fallback for it.

## 3. Verdict

- The runner criterion (B1 8-min 5/5): **PASS**.
- Plan §3 18.5, "no regression against B-8 on any gate": **FAIL**. Samples went from 4/4 at B-8
  to **3/4**, and B1 wall time regressed 2–5× (not a declared gate, but a real user-facing
  regression).
- **Per plan Amendment C, the `AI_MODE` default stays `local`.** `cloud_first` stays available as
  an **opt-in** on the Settings page. The owner decides the next step.

## 4. Options for the owner

| Option | What it takes | Effect |
|---|---|---|
| **A. Keep local as default; cloud_first opt-in** | Nothing | The current speed and reliability are kept. Cloud is available when wanted (about 5 scripts/day free). |
| **B. Tuning follow-up, then re-measure** | A small phase: a shorter cloud budget (e.g. 60 s; Super normally answers in 8–28 s); a 429 daily cap **opens the circuit until the next UTC day** (stops wasting calls); malformed cloud JSON → retry on the fallback | Fixes most of the slowness and the JSON death. It does not lift the 50/day cap. |
| **C. One-time $10 OpenRouter top-up** | $10, which stays on the account as balance; `:free` models remain free per call | The cap rises to **1,000 requests/day** (about 100 scripts/day). The owner has said no payment, so this is listed for completeness only. |
