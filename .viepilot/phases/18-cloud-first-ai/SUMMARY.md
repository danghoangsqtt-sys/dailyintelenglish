# Phase 18 Summary — Cloud-First AI with Local Fallback (ENH-011)

- **Status:** complete. Opened 2026-09-23, closed 2026-09-26. **Version 1.1.0-beta.**
- **Plan:** `docs/implementation/phase-18-cloud-first-ai.md` (Amendments A–G)
- **Decisions:** D21–D24 (cloud first, free tier, a generic provider, a Settings key), D27 (model
  chain), D28 (multi-provider), D30 (Gemini first), D31 (B-11 accepted).

## Outcome

The default is `AI_MODE=cloud_first`. The chain is **Gemini 3.1 Flash-Lite → Gemini Flash-Lite
latest → OpenRouter free (Nemotron 3 Super → Gemma 4 → Dots3) → local qwen3.5:9b**. Each entry
has its own circuit (daily-quota-aware), each call has its own budget within a total cloud
budget, and local gets a fresh budget. The kill switch is `DIE_AI_ALLOW_CLOUD`; with no key, the
effective mode is local.

| Gate | Result |
|---|---|
| B-9 (Nemotron free only) | B1 5/5 but samples 3/4 and 2–5× slower; the 50/day free cap ran out mid-gate; fallback carried the rest |
| B-10 (OpenRouter → Gemini) | FAIL: **Gemini served 0 calls**, because the OpenRouter-only `reasoning` param was rejected with 400 |
| **B-11 (Gemini first)** | **11/11 complete, B1 median 45 s (vs ~150 s local), repetition 0, media PASS.** The runner FAIL was only outro-heuristic false negatives (verified), and the owner accepted it as PASS |

Suite 964 → **1175**. Every task was PM-reviewed with independent revert checks.

## Lessons

- **Probe with the app's exact request.** The B-10 bug passed MockTransport tests and a
  hand-written probe. 18.9 added an opt-in live contract check built from the real provider
  class; run it before every gate.
- **Free tiers are account-wide and policy-bound.** OpenRouter's `:free` cap is one counter for all
  free models, and OpenCode Zen's free tier is restricted to the OpenCode client (403). Only
  separate providers add volume, and a provider's terms are never worked around.
- **Tests must never hold real keys.** The pytest process loaded `.env` at import (N1). Secrets are
  now neutralised for the whole session, and guard assertions print lengths only (N2).

## Follow-ups

- **ENH-014:** the runner outro heuristic, to decide before the next gate.
- **ENH-015:** Gemini's first pass lands at 0.61× the section target (one repair per section).
- The per-provider fallback-rate breakdown in `get_fallback_rate_stats` (deferred in 18.8).
- The live contract check always exits 0 (nit).
