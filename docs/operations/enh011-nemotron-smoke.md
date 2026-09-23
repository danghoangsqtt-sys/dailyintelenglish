# ENH-011 Smoke Test — Free Cloud Models via OpenRouter (2026-09-23, PM)

The owner's OpenRouter key is stored as `DIE_OPENAI_COMPAT_API_KEY` in `.env`, which is
gitignored and was never printed. The key is on the free tier. No app code was changed: the tests
used scratch scripts only (a provider plugged into the real pipeline through the trial runner,
plus direct probes). Evidence is in `data/quality_reviews/phase15/nemotron-*-smoke/` (gitignored).

## 1. API behaviour (OpenRouter, `https://openrouter.ai/api/v1/chat/completions`)

- **JSON:** use plain prompt-only JSON.
  - `response_format: json_schema` returned **malformed JSON** (`[[{…`, `[{"speaker[{…`) and ran slowly (30–76 s).
  - `json_object` forces a single object, which breaks our array contract.
  - A plain prompt asking for JSON returned a valid array.
- **Upstream errors come back as HTTP 200 with an `error` body** (e.g. `503 Service temporarily
  overloaded`). A provider must treat that as a transient error.
- **Reasoning:** Nemotron models reason before answering. Setting `reasoning: {"exclude": true}`
  keeps the reasoning out of `content`. `enabled: false` on Lightning broke the JSON.

## 2. Full pipeline run (real script job, B1 8-min, same runner as the gates)

| Model (free) | Result |
|---|---|
| Nemotron 3 Ultra | **error**: 7 of 8 calls were `503 overloaded`; section 1 exceeded the router's 120 s deadline |
| Nemotron 3.5 Lightning | **error**: the outline took 116 s; section 1 exceeded the 120 s deadline |

## 3. Single-section probe: 10 free models, same B1 section task (target 200 words, JSON array)

| Model (free) | Result | Latency | Words (target 200) |
|---|---|---|---|
| nvidia/nemotron-3-super-120b-a12b | OK | 28 s (8 s in an earlier outline probe) | **199 (0.99×)** |
| nvidia/nemotron-3-ultra-550b-a55b | OK | 136 s | **199 (0.99×)** |
| nex-agi/nex-n2.5-pro | OK | 296 s | 203 (1.01×) |
| dots-studio/dots-3-note-preview | OK | 70 s | 171 (0.85×) |
| nvidia/nemotron-3.5-lightning | timeout | > 180 s | — |
| qwen/qwen3.8-27b, z-ai/glm-5.2, google/gemma-4-31b-it, google/gemma-4-26b-a4b-it | 429 rate-limited | — | — |
| thinkingmachines/inkling | 403, restricted access | — | — |

All successful outputs were valid JSON with correct speaker alternation (max run 1).

**For comparison, local qwen3.5:9b** (B-6 + B-7, 118 sections): its first-pass generation lands at
a median **0.60×** target, with only 15/118 within ±15%. The large cloud models hit the word target
almost exactly on the first pass, which is the weakness Phase 17 is working around. This is a
single sample per model, so treat it as indicative, not measured.

## 4. Conclusions

1. **Quality and instruction following:** much better than local qwen, and would likely remove
   most of the repair churn.
2. **Free-tier reliability:** too poor to be the *primary* provider on its own. The failures were
   overloads (503), 429s, 30 s–5 min latency, and restricted models. A script job makes 10–15
   calls under a 120 s per-call deadline, and one bad call fails the job.
3. **Paid variants are cheap** (OpenRouter list prices, per 1M tokens):
   - Nemotron 3 Super: $0.08 input / $0.45 output
   - Nemotron 3 Ultra: $0.60 input / $2.40 output
   - Nemotron 3.5 Lightning: $0.08 input / $0.20 output

   A rough estimate for one script job (~45k input + ~15k output tokens) is about **$0.01 with
   Super** or **$0.06 with Ultra**. This is an estimate; the real figure must be measured.
4. **Recommended ENH-011 design:**
   - one OpenAI-compatible provider with a configurable model (default **Nemotron 3 Super**);
   - a cloud-specific call deadline (about 180 s);
   - bounded retry on 503/429/200-with-error;
   - **local qwen as automatic fallback**, so a free-tier outage degrades instead of failing;
   - then an A/B gate. Phase 17 still matters because qwen stays the fallback.
