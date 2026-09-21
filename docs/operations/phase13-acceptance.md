# Phase 13 Gate B — Operational Trial Acceptance Report

- **Run date:** 2026-09-21 (00:09:03Z – 00:23:57Z UTC, ~14m 54s wall clock)
- **Runner:** `scripts/run_ai_operational_trial.py` (Task 13.9)
- **Machine config at run time:** `AI_MODE=local` (fallback OFF — Gate B's own requirement),
  Ollama reachable, `qwen3.5:9b` present, digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7` (matches Task 13.1's
  Gate A evidence exactly).
- **Server:** real in-process `uvicorn` on an isolated port; the developer's own dev
  server on port 8000 was never touched. Every call in this trial was real HTTP via
  `httpx` — no `TestClient`, no mocked provider.
- **Raw machine-readable evidence (gitignored, not in this repo):**
  `data/quality_reviews/phase13/gate-b/gate-b-20260921T000903Z.json`

## Decision: **FAIL**

Local-first script generation (Ollama `qwen3.5:9b`, current section-generation prompts
and ±15% word-tolerance validator) does not meet Gate B's declared reliability bar. Per
the controlling plan (`docs/implementation/phase-13-local-first-ai-reliability.md`,
section 8, Task 13.9's own decision rule): **local stays experimental; the packaged/
production default remains Gemini-primary** (already the case — `AI_MODE` default is
`"gemini"`, per ADR-001 point 6). No threshold was weakened to reach this decision.

## What was run

| Set | Count | Completed | Passed content checks |
|---|---:|---:|---:|
| B1, 8-minute (the primary Gate B set) | 5 | 1 | 0 |
| B1, 5-minute (sample) | 1 | 0 | — |
| B1, 10-minute (sample) | 1 | 0 | — |
| A2, 8-minute (sample) | 1 | 0 | — |
| C1, 8-minute (sample) | 1 | 0 | — |
| Learning generation (from the 1 completed script) | 1 | 1 | 1 (spot check) |
| Real Edge TTS → audio → video pipeline | — | not run | no passing project to run it against |

## Root cause

**8 of the 9 real script-generation attempts failed the exact same validator, for the
exact same reason: a single generated section's word count fell outside the
pipeline's own ±15% tolerance of that section's target** (`app/services/script_pipeline.py::
validate_section`, `SCRIPT_SECTION_WORD_TOLERANCE = 0.15`,
`app/core/constants.py`). This is not a system/infrastructure defect — the local
runtime, provider gateway, durable job machinery, checkpointing, and cancellation all
worked correctly throughout (confirmed by reading every job's full status/timeline).
It is a **content-quality reliability gap in the local 9B model's ability to follow a
precise word-count instruction for one short (~1–2 minute, ~145–208 word) section**,
and the pipeline's single allowed repair pass did not correct it in any of these 8
cases:

| Run | Target words | Actual words | Miss |
|---|---:|---:|---:|
| B1 8-min #1 | 160 | 240 | +50% |
| B1 8-min #2 | 160 | 249 | +56% |
| B1 8-min #3 | 160 | 195 | +22% |
| B1 8-min #4 | — | — | **passed** (785 total words, all content checks except one heuristic false positive — see below) |
| B1 8-min #5 | 160 | 41 | −74% |
| B1 5-min (sample) | 166 | 132 | −20% |
| B1 10-min (sample) | 143 | 77 | −46% |
| A2 8-min (sample) | 145 | 183 | +26% |
| C1 8-min (sample) | 208 | 252 | +21% |

Misses go both directions (badly over and badly under target) and occur across every
CEFR level tested (A2/B1/C1) and every duration tested (5/8/10 minutes) — this is a
general local-model instruction-following limitation for this specific constraint, not
a bug isolated to one configuration.

**On the one script that did complete** (B1, 8 minutes, 785 words — inside the
720–880-word global range): every runner-side content check passed except one, which
on inspection is a **false negative in this trial's own runner heuristic**, not a real
content defect. The runner's `has_outro` check looks for a fixed set of farewell
phrases (`"thanks for"`, `"see you"`, `"goodbye"`, etc.); the script's actual last line
— *"Good luck with your journey to better health and longer life ahead."* — is a
genuine, natural closing line that simply doesn't match that fixed phrase list. This is
disclosed for accuracy; it does not change the overall decision, since even crediting
this one run as a full pass leaves the primary set at 1/5 complete and 1/5 passing
content checks, far below the required 5/5 complete and ≥4/5 passing.

## Gate B thresholds checked (controlling plan section 8)

| Threshold | Result |
|---|---|
| 5/5 B1-eight-minute runs complete, no crash/unrecoverable schema failure | **1/5** — FAIL |
| ≥4/5 of those pass content checks (720–880 words, 35–65% speaker balance, no exact duplicate, <1% repeated 8-gram, intro+outro, human CEFR pass) | **0/5 mechanically confirmed** (1/5 would likely pass on human review of the outro line) — FAIL |
| First durable progress ≤90s | **PASS** for every run that started (observed 0.01–0.02s to first stage change) |
| No section exceeds 5 minutes / total script ≤20 minutes | **PASS** for every run (longest observed job: 180.7s ≈ 3 minutes) |
| Learning: 5/5 deterministic checks, no critical human-reviewed defect | Only 1 learning job was run (only 1 script completed to generate learning from) — it passed its deterministic spot check (non-empty vocabulary/idioms/grammar/questions, no duplicate vocabulary). **Not evaluated at n=5** as the plan specifies, since there were not 5 completed scripts to run it against. Human review of Vietnamese/IPA/grammar content is a separate manual step, not performed by this automated runner. |
| Real Edge TTS → MP3 → midnight 16:9 MP4 pipeline, 432–528s, ≤1.0s A/V diff, correct codecs | **Not run** — Gate B requires running this against "the winning configuration," and no configuration won |
| No server ERROR/traceback | Tracebacks did appear in the server log for every failed job — but they are the pipeline's own expected, handled `SchemaValidationError`-family exceptions, logged by `ai_worker.py`'s existing error-handling path (job correctly transitions to `status=error` with a safe `error_code`/`error_message`, never a 5xx to any HTTP caller, never a hang). This is the pipeline behaving exactly as designed when content validation fails, not an unhandled crash. |

## What did work correctly

- The whole durable-job architecture (Tasks 13.2–13.6): every failed job transitioned to
  `error` cleanly with a specific `error_code` (`section_validation_failed`) and a safe
  `error_message`, in every case within 3 minutes, with zero hangs, zero unhandled 5xx
  responses to the trial's HTTP calls, and zero partial/corrupt script writes (a failed
  job never touched the project's persisted script — confirmed by construction, since
  `script_pipeline.py` only performs its final atomic save after every section and the
  global merge validate cleanly).
- `GET /api/ai/health` correctly reported `mode: "local"`, `ollama_reachable: true`,
  and the exact qualified model/digest throughout, never exposing a secret.
- The one script that did complete produced coherent, on-topic, correctly speaker-
  attributed dialogue with zero duplicate lines and zero repeated phrasing — the
  model's actual language quality is not in question here, only its word-count
  precision at the section level.
- Learning generation, when it ran, produced a complete, non-empty, non-duplicate pack
  on the first attempt.

## Recommendation

Ship Task 13.10 (rollout/docs/rollback) with the **Gemini-primary, local-experimental**
path the controlling plan already designates for a Gate B failure — this is not a
setback for Phase 13 as a whole: the durable-job architecture, provider gateway, and
cloud-fallback compatibility work (Tasks 13.2–13.8) all pass their own gates
independently of Gate B's local-model-quality question, and remain valuable and in use
regardless of which provider is primary.

Whether to invest further time tuning the local model's word-count reliability (e.g. a
follow-up task revisiting `prompts/script/section.txt`'s word-budget instruction
wording, or trying the plan's own listed remediation order for Gate A-class memory
issues does not apply here since this is a content-quality gap, not a memory one) is a
product decision outside this report's scope — recorded as an open question for the
project owner, not decided unilaterally here, since it would require reopening
`script_pipeline.py`'s prompts (outside Task 13.9's allowed files) and is not required
by the controlling plan before proceeding to Task 13.10.
