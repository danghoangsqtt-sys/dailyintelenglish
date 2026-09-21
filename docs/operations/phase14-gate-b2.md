# Phase 14 Gate B-2 — Second Operational Trial, Both Providers

- **Task:** 14.4b (PM/Tester execution). Runner prepared by the Coder in 14.4a.
- **Controlling protocol:** `docs/implementation/phase-14-ai-gateway-resilience.md` §4.4
  (decision rules declared before any run; Amendment C recorded before any run).
- **Run date:** 2026-09-21 (local matrix 08:07–08:41Z; Gemini matrix 08:41–08:53Z UTC)
- **Runner:** `scripts/run_ai_operational_trial.py --matrix local|gemini` at code HEAD
  `153aa16` (real in-process `uvicorn` on an isolated port, real HTTP, no mocks, isolated
  `DIE_DATA_DIR`). Every number below is traceable to the evidence files at the end.
- **Status of this report:** script and learning gates are final for both providers. The
  **media pipeline step is pending** — the runner crashed on a runner-side defect (§2.4)
  and will be re-run with `--media-only` once the Coder's 14.4a-c fix lands; this file is
  then updated.

## 1. Preflight (recorded before run 1)

| Check | Result |
|---|---|
| HEAD | `64bab3b` (code HEAD `153aa16` + PM state commit); worktree clean; upstream `origin/main` |
| Full suite at this HEAD | **865 passed**, 0 failed, 8m27s; `ruff check app tests scripts` clean (PM-run; user confirmed the Coder idle) |
| Ollama | serving `qwen3.5:9b`, digest `6488c96fa5fa`, 6.59 GB — matches Gate A; env already correct, no restart |
| GPU baseline | 1,844 / 12,288 MiB used before the local matrix |
| Dev server port 8000 | not answering at trial time; never touched (runner uses ports 65400 / 54805) |
| Gemini probes (3 × `gemini-3.8-flash:generateContent`) | `200 (3.55 s) → 503 (3.37 s, "currently experiencing high demand… temporary") → 200 (9.72 s)` — same transient pattern as the Phase 13 diagnostic; no rate-limit headers |
| Gemini quota | Not readable from the API before the run; the user did not report a dashboard value. Declared before the Gemini matrix: a `429` daily-quota response would split the matrix 3 + 2 across two days. **Post-run probe** (§3.3) shows the real limit: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, **quotaValue 20** |
| Sequence | local matrix first (Ollama, fallback OFF) → Gemini matrix; never concurrent; Coder idle throughout |

## 2. Local matrix (`--matrix local`, Phase 13 §8 Task 13.9 protocol verbatim)

Evidence: `gate-b2-20260921T080706Z.json`, `local-matrix-console.log`.

### 2.1 Primary set — five B1 eight-minute jobs (`AI_MODE=local`, fallback OFF)

| Run | Status | `error_code` | Class | Seconds | Total words | Repairs | Router calls / attempts | Backoff absorbed |
|---|---|---|---|---:|---:|---:|---|---|
| 1 | **complete** | — | — | 246.9 | **817** | 4 | 10 / 11 (max 2 on one call) | 1 × `ProviderTimeoutError` (Ollama 60 s) absorbed, 1.0 s |
| 2 | **complete** | — | — | 156.6 | **780** | 5 | 11 / 11 | — |
| 3 | error | `section_validation_failed` | content | 165.6 | — | 4 | 9 / 9 | — |
| 4 | error | `global_validation_failed` | content | 198.8 | (1053) | 4 | 10 / 10 | — |
| 5 | **complete** | — | — | 162.7 | **722** | 4 | 10 / 10 | — |

- Run 3: "more than 5 consecutive lines from one speaker" survived the one repair — a
  *structural* section check, unchanged by 14.3, correctly still fatal.
- Run 4: the final section came back at **426 words against an effective target of 173**
  (340 before its repair — the repair made it longer). Total 1053 = +31.6%. The global ±10%
  gate did exactly its job. `repair_count = 4` = 3 per-section repairs + the one
  final-section budget repair (14.3 item 6), which also failed to shorten it.
- Every completed job passed **all** runner content checks (720–880 words, speaker share
  35–65%, no duplicate line, 8-gram ratio < 1%, intro, outro). First durable progress
  0.01–0.02 s; longest stage gap 36–138 s (< 5 min); longest job 247 s (< 20 min).
- **Infra failures: 0. `handler_exception`: 0.** The one infrastructure event (an Ollama
  request timeout in run 1) was absorbed by 14.1's backoff on attempt 2.

### 2.2 Per-section behaviour (all 23 sections of the primary set, from checkpoint `metrics_json`)

| Run | Section words (nominal 160 each) | Effective targets | Notes |
|---|---|---|---|
| 1 | 106, **417**, 90, 107, 97 | 160, 214, 104, 104, 80 | s2 +95% over effective; budget clamped later sections down; landed 817 |
| 2 | 169, 141, 116, 160, 190 | 160, 151, 161, 206, 214 | smooth carry; landed 780 |
| 3 | 175, 115, 172 | 160, 145, 175 | died on structure at s3 |
| 4 | 146, 197, 144, 140, **426** | 160, 174, 151, 158, 173 | s5 +146% over effective, twice |
| 5 | 125, 192, 118, 242, **43** | 160, 195, 198, 216, 123 | s5 −65%; still landed 722 |

Aggregates (runner): within ±15% of *nominal* **34.8%** (8/23); mean deviation vs nominal
+4.0%; **σ 55.7%** (driven by the 417/426/404-word outliers); repair success rate (repair
ended inside ±15% of the effective target) **44.4%** (8/18); total repairs 21; totals inside
720–880: **3/3** completed.

The Phase 13 figure (66.7% per-section pass, 18/27) counted only sections that *passed*
the old hard gate; this run checkpoints every accepted section, so the two rates are not
directly comparable. What is comparable: job completion **1/5 → 3/5**, and the
running budget converted two jobs with wildly off-target sections (runs 1 and 5) into
in-range totals.

### 2.3 Samples and learning

| Run | Status | Total words / target | Runner `all_checks_pass` |
|---|---|---|---|
| B1 5-min | complete, 162.8 s | 453 / 500 (−9.4%) | false — `word_count_in_range` false and `has_outro` false |
| B1 10-min | complete, 310.3 s | 1084 / 1000 (+8.4%) | false — `word_count_in_range` false |
| A2 8-min | error `section_validation_failed` (structural), 135.6 s | — | — |
| C1 8-min | complete, 186.7 s | 980 / 1040 (−5.8%) | false — `word_count_in_range` false |

**Runner defect 2 (disclosed, not a pipeline defect):** the runner's `word_count_in_range`
uses the fixed B1-eight-minute range 720–880 for every run, so all three completed samples
are marked failing although each is inside ±10% of its own target (and each *passed the
pipeline's own* `validate_global`, which is why it completed). Samples are informational,
not gate items; the evidence field is misleading and the Coder is fixing it (14.4a-c).

Learning: **2/3** complete (one `pack_validation_failed`: a vocabulary example sentence and
an idiom not found in the transcript — grounding check working as designed).

### 2.4 Media pipeline — not executed (runner defect 1)

`POST /api/projects/99de9ef7…/audio/generate` returned 500; the trial DB's `audio_jobs`
row says `Line(s) not yet synthesized: …`. The runner never calls the per-line TTS
endpoint (`POST /api/projects/{id}/tts/preview`) before mixing — a latent defect since
Task 13.9, invisible then because Phase 13 never reached the media step. The Coder is
adding the TTS step and a `--media-only PROJECT_ID` flag; the PM will run it against the
completed 817-word project and update §2.4 and §4.

### 2.5 Local decision (Phase 13 rule verbatim, unchanged)

**FAIL** — 3/5 complete (needs 5/5), 3/5 content-pass (needs ≥ 4/5), media not yet run.
No threshold was weakened. Local stays experimental.

## 3. Gemini matrix (`--matrix gemini`, `AI_MODE=gemini`)

Evidence: `gate-b2-20260921T084153Z.json`, `gemini-matrix-console.log`.

### 3.1 Runs

| Run | Status | `error_code` | Seconds | What happened (from router logs and `metrics.calls[]`) |
|---|---|---|---:|---|
| 1 | error | `provider_unavailable` | 105.5 | outline: 503 ×3 → **succeeded on attempt 4** (7.0 s backoff); section 1 OK on attempt 1; section 2: 503 ×4 → exhausted |
| 2 | error | `provider_unavailable` | 45.2 | outline OK first try; section 1: 503 ×4 → exhausted |
| 3 | error | `provider_unavailable` | 48.2 | outline: 503 ×3 → succeeded on attempt 4; section 1: **429 ×3 then 503** on attempt 4 → exhausted (the last error, a 503, sets the code) |
| 4 | error | `provider_rate_limited` | 12.1 | outline: 429 ×4 → exhausted |
| 5 | error | `provider_rate_limited` | 12.1 | outline: 503 then 429 ×3 → exhausted |

Note on run 3: the router re-raises the *last* exception of an exhausted route. Its
section-1 sequence was 429, 429, 429 (three sleeps logged as `ProviderRateLimitError`) and
a 503 on attempt 4, so the job row says `provider_unavailable` / "temporarily overloaded".
The classification is `infra` either way; the mixed sequence itself is the point — once
the daily quota was gone (§3.3), 429 and 503 interleaved.

Totals from the console log: **21 backoff sleeps** (7 sequences × 1 + 2 + 4 s = 49 s
slept in total), **5 exhaustions**, 2 sequences that ended in success (both outlines on
attempt 4). Evidence `total_backoff_seconds = 14.0` counts only calls that ended `ok`;
error-outcome call records carry no `attempts`/`backoff_seconds` (design gap noted for
14.1-b/14.2: the router's raised exception should carry the attempt count).

### 3.2 Aggregates

Completion 0/5; infra deaths **5/5** (3 × 503-exhaustion, 2 × 429); `handler_exception` 0;
max attempts observed 4; content checks not reachable.

### 3.3 Root causes — two, and they compound

1. **The backoff window is too short for Gemini's real 503 storms.** 1 + 2 + 4 s of sleep
   plus ~3 s per 503 response ≈ 20 s of coverage. Two outlines survived (the storm ended
   inside the window); three section calls did not. The 120 s request deadline had ≈ 100 s
   of unused budget in every one of those deaths. This reopens Task 14.1 exactly as the
   declared rule says.
2. **The account is on the Gemini free tier: 20 requests per day per model.** A single
   post-run probe returned HTTP 429 with
   `quotaId = GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue = 20`,
   `retryDelay = 21s`. Every *attempt* counts: the matrix made ≈ 30 requests (run 1 alone
   made 9) on top of 4 probes, so the daily cap was exhausted during run 3. Runs 4–5 were
   killed by quota, not by overload. Retrying a daily-quota 429 with a 1–4 s backoff only
   burns more quota; the router cannot currently tell a per-minute 429 from a per-day one.

These are independent: with unlimited quota, cause 1 alone had already produced two
deaths (FAIL-INFRA threshold) before the first 429.

### 3.4 Gemini decision (Amendment C rule, declared before the run)

**FAIL-INFRA** — 5 infra deaths (≥ 2). Reopens 14.1; blocks 14.6. Content quality of
Gemini output could not be measured at all (0 completed jobs).

## 4. Decisions and consequences

| Provider | Verdict | Rule | Consequence |
|---|---|---|---|
| Local (`qwen3.5:9b`) | **FAIL** (3/5 complete, 3/5 pass; media pending) | Phase 13 §8 13.9, unchanged | stays experimental; clear improvement over Phase 13 (1/5 → 3/5) and the first measured repair/backoff telemetry |
| Gemini (`gemini-3.8-flash`) | **FAIL-INFRA** (0/5, 5 infra deaths) | Amendment C | reopens 14.1; 14.6 stays blocked |

Per plan §6 (14.6 table) row "FAIL / FAIL-INFRA": **stop condition — Task 13.10 stays
blocked.** Per plan §8, two declared stop conditions fired: "Gate B-cloud returns
FAIL-INFRA after 14.1" and "the Gemini account's live quota cannot accommodate the declared
matrix even split across two days" (20 requests/day cannot hold five jobs that each need
6–10+ requests). The PM stops here and reports; the decisions below are the user's.

## 5. What the evidence says to do next (PM recommendation, not a decision)

1. **14.1-b (code, Coder):** (a) honour Gemini's `retryDelay` on 429 (the body carries it;
   the plan's optional `retry_after_seconds` hint is now evidence-backed); (b) treat a 429
   whose `quotaId` contains `PerDay` as **non-retryable** (`provider_quota_exhausted`, a new
   error code) — retrying it only burns quota; (c) widen the 503 window inside the existing
   120 s deadline, e.g. up to 6 attempts with 1, 2, 4, 8, 16 s (31 s slept) — still
   ADR-001-A1-compliant (same model, one deadline); (d) make error-outcome call records
   carry `attempts`/`backoff_seconds` and re-raise a consistent exception class after a
   mixed sequence.
2. **Account (user):** Gemini-primary is not viable on a 20-requests/day free tier for
   *any* backoff design — one eight-minute script needs 6–10+ requests. Either enable
   billing (pay-as-you-go lifts the per-day cap) or keep Gemini as fallback-only. This is
   a product/billing decision outside the PM's authority.
3. **Local model:** the running budget works when the model is roughly responsive; the
   remaining killers are (i) sections that come back at 2–3× the requested length even
   after repair, and (ii) the structural ">5 consecutive lines" rule. Candidate follow-ups
   (not started): a hard per-section *ceiling* repair prompt ("cut to N words"), and
   asking the −9% question from the plan with this data: mean deviation vs nominal is
   now +4.0%, so **no** systematic undershoot compensation is warranted — the problem is
   variance, not bias. Open question closed on evidence.
4. **Attempts (open question "3 vs 4"):** 4 is not enough for Gemini; see 1(c).

## 6. Evidence

| File | SHA-256 |
|---|---|
| `data/quality_reviews/phase14/gate-b2/gate-b2-20260921T080706Z.json` (local) | `1396833c823b994424cd57fa0d67d10da04ae31e2c4b7b85b10b4459b8a758e7` |
| `data/quality_reviews/phase14/gate-b2/gate-b2-20260921T084153Z.json` (Gemini) | `bc2f74aa25120789cf23243a7c58ba9dce30867d248af5223003f19066421964` |
| `data/quality_reviews/phase14/gate-b2/local-matrix-console.log`, `gemini-matrix-console.log` | server + runner console (contain no key; prompts never logged) |
| `data/quality_reviews/phase14/gate-b2/trial-data/app.db` | trial DB with all jobs/checkpoints (kept for review; gitignored) |

All evidence is gitignored and kept locally, per the Gate A/Gate B precedent.
