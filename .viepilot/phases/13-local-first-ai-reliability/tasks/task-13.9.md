# Task 13.9 — Real No-Mock Bake-Off and Operational Trial (Gate B)

- **Status:** done
- **Gate B decision:** FAIL (local stays experimental; Gemini remains primary) — see
  `docs/operations/phase13-acceptance.md` for the full report.
- **Dependency:** 13.1–13.8 (all done)
- **Controlling detail:** implementation plan §8, Task 13.9

## Objective

Use live uvicorn HTTP and real providers to decide local-primary versus experimental,
then complete a real eight-minute script → every-line Edge TTS → MP3 → midnight 16:9
MP4 run. Never use TestClient, pytest, mocks, or assumed completion.

## Allowed files/runtime effects

Operational runner, acceptance report, ignored JSON/CSV/log/media evidence, and created
project/media/database rows. Do not delete the test project; keep review server running.

## Gate B

Use every fixed threshold in the controlling plan: five local-only B1 eight-minute
runs, 4/5 content/performance pass, 5/5 deterministic learning checks plus human review,
and ffprobe-readable 432–528s audio/video with ≤1.0s A/V difference and no server
ERROR/traceback. Record IDs, digest/settings, timings, repairs/fallbacks, resource peaks,
bytes, hashes, durations, codecs, and all warnings. Do not weaken thresholds post hoc.

## Pre-implementation findings and file-level plan (doc-first gate)

**Evidence path (deviation from the plan's literal `artifacts/phase13/gate-b/*`):**
`artifacts/` is not in `.gitignore` and this task's allowed-file list does not include
`.gitignore` itself. Task 13.1 hit the identical situation and used
`data/quality_reviews/phase13/gate-a/` instead (already gitignored via the existing
`data/quality_reviews/` entry). Following that established precedent: this task's
evidence lands under `data/quality_reviews/phase13/gate-b/`, not `artifacts/`.

**API surface confirmed by reading the real routes before writing the runner:**
- `POST /api/projects` creates a project from `ScriptConfig` (topic/cefr_level/genre/
  accent/duration_minutes/num_speakers/speakers/language_features).
- `POST /api/projects/{id}/ai-jobs {"operation": "script"|"learning"}` → 202/200;
  `GET .../ai-jobs/{job_id}` polls `AIJobOut` (status/stage/progress/provider/model/
  fallback_used/attempt/repair_count/error_code/error_message/timestamps) until a
  terminal status (`complete|error|cancelled|stale`).
- `GET /api/projects/{id}/script` / `GET /api/projects/{id}/learning` fetch the
  persisted result once the job is `complete`.
- `POST /api/projects/{id}/audio/generate` already synthesizes **every line via real
  Edge TTS internally** (`audio_service.mix_project`, existing Phase 1 code, unchanged)
  and mixes to MP3/WAV — no separate per-line TTS call is needed from the runner.
- `POST /api/projects/{id}/video/generate {"template_id": ..., "aspect_ratio": "16:9"}`
  renders the burned-in-subtitle MP4 from the completed audio job.
- `GET .../audio/download`, `GET .../video/download` return the real bytes to hash/
  `ffprobe`.
- `CEFR_WORDS_PER_MINUTE["B1"] = 100` (`app/core/constants.py`, unchanged file) confirms
  B1 eight minutes targets ~800 words, matching the plan's own stated figure.

**Runner design (`scripts/run_ai_operational_trial.py`):**
1. Start a real `uvicorn` server as a subprocess on a fixed non-8000 port (e.g. 8020),
   with `DIE_AI_MODE=local` in its environment (fallback OFF, per Gate B's own
   requirement) and a dedicated `DIE_DATA_DIR` so the trial's real projects/media never
   touch the developer's existing `data/` tree. Poll `GET /health` until it answers
   before issuing any other call — no `TestClient`, no mocks, only real `httpx` calls
   over real HTTP, per the plan's explicit constraint.
2. For each of the 5 consecutive B1-eight-minute runs: create a fresh project (2
   speakers, `interview` genre, `american` accent — matches the existing golden-input
   convention from Task 13.0's fixtures), create the `script` job, poll until terminal,
   and record: job id, timings (created/started/finished, first-progress latency,
   longest section duration), `actual_provider`/`model`/`fallback_used`/`repair_count`,
   and any `error_code`/`error_message`.
3. On each completed script, run the runner's own content checks (independent of the
   pipeline's internal validators, since Gate B is measuring outcomes, not re-trusting
   the code under test): total word count (720–880), per-speaker word share (35–65%
   for two speakers), zero exact-duplicate lines, normalized repeated-8-gram ratio
   (<1%), and presence of an intro/outro line. Record pass/fail per check, not just an
   overall verdict.
4. Then one B1-five-minute run, one B1-ten-minute run, one A2-eight-minute run, and one
   C1-eight-minute run (each once — "samples", not a repeated bake-off), same recording.
5. Run 5 learning-generation jobs against 5 of the completed scripts above (reusing them
   rather than generating 5 more just for learning), checking the pipeline's own
   deterministic outcome (complete without error, grounding/count/duplicate/answer
   validators already enforced internally by `learning_pipeline.py`) plus a runner-side
   spot check (non-empty vocabulary/idioms/grammar/questions, no duplicate vocabulary
   entries) — full linguistic/CEFR human review is explicitly out of scope for an
   unattended runner and is flagged in the report as a manual follow-up, not silently
   marked done.
6. For the winning configuration (the B1-eight-minute run set, assuming ≥4/5 pass): run
   one real `POST audio/generate` → `POST video/generate` → download both → SHA-256 +
   size + `ffprobe -v error -show_format -show_streams -of json` on each, checking
   432–528s duration, ≤1.0s A/V difference, expected H.264/AAC codecs, and scanning the
   server's own log output captured since this subprocess started for `ERROR`/traceback
   lines.
7. Write `data/quality_reviews/phase13/gate-b/gate-b-<UTC timestamp>.json` (the full
   machine-readable evidence — no secrets, no full prompts) and
   `docs/operations/phase13-acceptance.md` (the human-readable pass/fail report, per
   Gate B's declared thresholds, decision, and any deviations).
8. Stop the trial's own uvicorn subprocess at the end (or on a fatal error) — never the
   real developer dev server already listening on port 8000, which this script never
   touches.

**Explicitly out of scope for this automated runner (recorded, not hidden):** the
"human CEFR rubric" pass and "no critical human-reviewed Vietnamese/IPA/grammar/answer
defect" clauses of Gate B require an actual human read of the generated content: the
runner produces the real generated artifacts and its own deterministic-check results,
but the human-review clauses are completed as a separate step after the runner
finishes, using the runner's own saved script/learning JSON, not invented or assumed
by the runner itself.

## Verification and exit

Real `httpx` calls to a real live `uvicorn` process only; the runner never imports
`fastapi.testclient` or monkeypatches a provider. Every threshold above is checked
mechanically and recorded, never eyeballed. `docs/operations/phase13-acceptance.md`
states an explicit PASS/FAIL decision citing the exact failing criterion if not PASS.
Do not delete the trial's projects; keep the review server's data reachable afterward.

## Results (2026-09-21)

`scripts/run_ai_operational_trial.py` was smoke-tested first (`--smoke-test`, 1
abbreviated run) to validate the mechanics before committing to the full multi-hour
trial -- this caught one real infrastructure regression before it could taint results:
an earlier ad hoc Ollama restart (during Task 13.8's packaged-exe verification) had
started `ollama.exe serve` without the persisted `OLLAMA_MODELS` user environment
variable, silently pointing it at an empty model directory (`qwen3.5:9b` reported
"missing" even though it was never uninstalled). Fixed by restarting Ollama with every
persisted env var (`OLLAMA_HOST`/`OLLAMA_MODELS`/`OLLAMA_MAX_LOADED_MODELS`/
`OLLAMA_NUM_PARALLEL`/`OLLAMA_MAX_QUEUE`/`OLLAMA_NO_CLOUD`) explicitly set before
`serve`, then reconfirmed via `/api/tags` that the digest matched Task 13.1's Gate A
evidence exactly before running the real trial.

The full trial ran `AI_MODE=local` (fallback OFF) against a real in-process `uvicorn`
server on an isolated port -- 5 B1-eight-minute runs, 4 samples (B1 5-min, B1 10-min,
A2 8-min, C1 8-min), and 1 learning generation, all via real HTTP, no mocks. **Result:
8 of 9 script-generation attempts failed the same validator** --
`script_pipeline.py::validate_section`'s ±15% section word-count tolerance -- with
misses in both directions (from −74% to +56% of the section's target word count) and
across every CEFR level and duration tested, not isolated to one configuration. The
single allowed repair pass did not correct any of the 8 failures. This is a genuine
local-model instruction-following limitation, not an infrastructure defect: every
failed job transitioned to a clean `error` status with a safe `error_code`
(`section_validation_failed`) within 3 minutes, zero hangs, zero partial/corrupt
writes, zero unhandled 5xx responses -- the durable-job architecture from Tasks
13.2-13.6 behaved exactly as designed under real repeated failure. The one script that
did complete (785 words, within the 720-880 global range) failed only one runner-side
heuristic check (`has_outro`, a narrow keyword list that missed a genuine but
differently-phrased closing line -- disclosed as a runner limitation, not a real
content defect) and passed every other check. Since the primary B1-eight-minute set
never reached even 1 of the required 5 completions with all content checks passing (4
needed), the real Edge TTS/audio/video pipeline was correctly never run (no "winning
configuration" existed to run it against) -- honestly recorded as not-executed, not
fabricated.

**Gate B decision: FAIL.** Per the controlling plan's own decision rule, local stays
experimental and Gemini remains the primary/default path (already the packaged
default). No threshold was weakened to reach this decision; the full evidence,
root-cause analysis, and threshold-by-threshold table are in
`docs/operations/phase13-acceptance.md`. Raw machine-readable evidence:
`data/quality_reviews/phase13/gate-b/gate-b-20260921T000903Z.json` (gitignored, not
committed). Task 13.10 proceeds with the Gemini-primary/local-experimental rollout
path the controlling plan already designates for this outcome.
