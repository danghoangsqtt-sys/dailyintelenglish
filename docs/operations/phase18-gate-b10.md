# Phase 18 Gate B-10 — Multi-provider chain (OpenRouter → Gemini ×2 → local)

- **Task:** 18.7 (PM, Coder idle).
  - **Protocol:** Gate B-9 (5 × B1 8-min, 4 samples, learning, media, owner configuration ×2),
    run with `--matrix cloud_first`.
  - **Default chain (Amendment F):** OpenRouter (Nemotron 3 Super → Gemma 4 → Dots3, via the
    `models` array) → `gemini-3.1-flash-lite` → `gemini-flash-lite-latest` → local qwen3.5:9b.
- **Run date:** 2026-09-25 (≈ 07:0x – 08:4xZ). **Code HEAD:** `37a3658` (18.8 accepted), suite
  1159/1159. The OpenRouter free counter was fresh (0/50) at the start.
- **Pre-gate probe:** Gemma 4 `:free` returned an upstream 429 (not the daily cap). Every Gemma 4
  probe so far has been 429.
- **Evidence (gitignored):** `data/quality_reviews/phase15/gate-b10/`
  - `gate-b10-20260925T083040Z.json` (SHA-256
    `6ea6190dbbec364e235f77fd6814e868d36cceac432927e9da95e78cb4a2afb2`)
  - owner-config JSON, both console logs, `trial-data/app.db`
  - Secret-pattern scan of the evidence: **0 matches**.

## 1. Results

| Job | Status | Calls: Nemotron / Dots3 / Gemini / local | Wall time |
|---|---|---|---|
| B1 8-min 1 | complete, 1,028 w | 4 / 2 / 0 / 2 | 464 s |
| B1 8-min 2 | complete, 1,005 w | 5 / 0 / 0 / 2 | 389 s |
| B1 8-min 3 | complete, 1,019 w | 3 / 1 / 0 / 7 | 687 s |
| B1 8-min 4 | complete, 1,029 w | 1 / 0 / 0 / 9 | 386 s |
| B1 8-min 5 | complete, 1,018 w | 4 / 0 / 0 / 4 | 409 s |
| Sample B1 5-min | complete, 640 w | 3 / 0 / 0 / 2 | 295 s |
| Sample B1 10-min | complete, 1,251 w | 3 / 1 / 0 / 9 | 675 s |
| Sample A2 8-min | complete, 902 w | 0 / 0 / 0 / 13 | 130 s |
| Sample C1 8-min | **error**: repeated 8-gram 1.32% (on the **local** path) | 0 / 0 / 0 / 10 | 111 s |
| Owner config 1 | complete, learning ✓ | 0 / 0 / 0 / 18 | 187 s |
| Owner config 2 | complete, learning ✓ | 0 / 0 / 0 / 15 | 166 s |

Other results: learning 5/5 + owner 2/2; media PASS 467.3 s. The runner decision reads PASS.

**Answered calls:** Nemotron 23, Dots3 4, **Gemini 0**, local qwen 91 (of 118).

**Chain failures seen in the console:**
- OpenRouter: 16 × `ProviderTimeoutError` (75 s budget), 1 × `ProviderDailyQuotaError`;
- Gemini: **every call failed** with `ProviderInvalidResponseError` (both models, script sections,
  repairs and learning packs).

## 2. Root cause (verified): the provider sends an OpenRouter-only parameter to Gemini

`openai_compat_provider.py:277` always sends `reasoning: {"exclude": true}`. The PM reproduced it
with one direct call: Gemini's OpenAI-compatible endpoint returns **HTTP 400 INVALID_ARGUMENT
"Invalid JSON payload received. Unknown name "reasoning": Cannot find field."**

The provider mapped that 400 to `ProviderInvalidResponseError`, which the router treats as a
*content* error (one immediate retry). So each Gemini entry wasted two calls per request until its
circuit opened. After that, with OpenRouter also timed out, the chain was empty, and the fallback
reason was **mislabelled** `no_cloud_provider_configured` (58 calls) when it actually meant "all
cloud circuits open".

**Why it wasn't caught:**
- The 18.8 tests use MockTransport, which never rejects unknown fields.
- The PM's provider probe used a hand-written payload without `reasoning`, not the app's exact
  request.

*Lesson:* provider probes must send the app's exact request body.

## 3. Verdict: **FAIL** (Amendment D criteria)

| Criterion | Result |
|---|---|
| B1 5/5 | ✅ |
| Samples ≥ B-8 (4/4) | ❌ **3/4**. C1 died on repetition on the **local** path, a known variable class, not a cloud defect. |
| B1 median wall time ≤ 1.5× local | ❌ **409 s vs ~150 s local, 2.7×.** Driven by 16 × 75 s OpenRouter timeouts, and by Gemini never serving. |

**The `AI_MODE` default stays `local`** (Amendment C).

## 4. Fix list (proposed Task 18.9, then Gate B-11)

1. **Vendor-aware request body:** send `reasoning` (and the `models` array) only to OpenRouter;
   send plain OpenAI-compatible fields to Gemini. Add a per-vendor request-body contract test,
   plus an **opt-in live contract check** that the PM runs with real keys. It must stay out of
   the normal test suite.
2. **HTTP 400 `INVALID_ARGUMENT` / invalid request → a non-transient request error:** no content
   retry, and that entry's circuit opens.
3. **Fallback-reason label:** `all_cloud_circuits_open` vs `no_cloud_provider_configured`.
4. **Chain order (owner decision):** evidence favours **Gemini first**. Gemini answers in about
   4 s and hits the word target at about 1.00×, while Nemotron free timed out 16 times at 75 s
   today.
